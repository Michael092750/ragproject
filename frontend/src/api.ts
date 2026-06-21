// Client for the IndustryIQ backend API.
// Base URL is configurable so the same build works in dev and production.
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface Source {
  text: string;
  score: number;
  document: string | null;
}

export interface ConversationSummary {
  id: string;
  title: string;
}

export interface Turn {
  question: string;
  answer: string;
}

export interface Me {
  id: string;
  email: string;
}

// ---------------------------------------------------------------------------
// Token storage (the JWT lives in localStorage so a reload keeps you signed in)
// ---------------------------------------------------------------------------
const TOKEN_KEY = "iq_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// AuthContext registers a callback here so any 401 (e.g. an expired token)
// forces a logout from one place, no matter which call surfaced it.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  return {
    ...(extra ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function check(res: Response): Promise<Response> {
  if (res.status === 401) onUnauthorized?.();
  if (!res.ok) {
    let detail: string = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body; keep the generic message */
    }
    throw new ApiError(res.status, detail);
  }
  return res;
}

function getJson<T>(path: string): Promise<T> {
  return fetch(`${API_URL}${path}`, { headers: authHeaders() })
    .then(check)
    .then((res) => res.json() as Promise<T>);
}

function sendJson<T>(path: string, method: string, body?: unknown): Promise<T> {
  return fetch(`${API_URL}${path}`, {
    method,
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: body === undefined ? undefined : JSON.stringify(body),
  })
    .then(check)
    .then((res) => res.json() as Promise<T>);
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export async function register(email: string, password: string): Promise<string> {
  const data = await sendJson<{ access_token: string }>("/auth/register", "POST", { email, password });
  return data.access_token;
}

export async function login(email: string, password: string): Promise<string> {
  const data = await sendJson<{ access_token: string }>("/auth/login", "POST", { email, password });
  return data.access_token;
}

export function me(): Promise<Me> {
  return getJson<Me>("/auth/me");
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------
export async function listConversations(): Promise<ConversationSummary[]> {
  const data = await getJson<{ conversations: ConversationSummary[] }>("/conversations");
  return data.conversations;
}

export function createConversation(title = "New conversation"): Promise<ConversationSummary> {
  return sendJson<ConversationSummary>("/conversations", "POST", { title });
}

export function renameConversation(id: string, title: string): Promise<ConversationSummary> {
  return sendJson<ConversationSummary>(`/conversations/${id}`, "PATCH", { title });
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${API_URL}/conversations/${id}`, { method: "DELETE", headers: authHeaders() }).then(check);
}

export async function getHistory(id: string): Promise<Turn[]> {
  const data = await getJson<{ turns: Turn[] }>(`/conversations/${id}/messages`);
  return data.turns;
}

// ---------------------------------------------------------------------------
// Session documents
// ---------------------------------------------------------------------------
export async function listDocuments(id: string): Promise<string[]> {
  const data = await getJson<{ documents: string[] }>(`/conversations/${id}/documents`);
  return data.documents;
}

export async function uploadDocument(
  id: string,
  file: File,
): Promise<{ filename: string; chunks: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/conversations/${id}/documents`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  }).then(check);
  return res.json() as Promise<{ filename: string; chunks: number }>;
}

// ---------------------------------------------------------------------------
// Streaming a reply (POST + Server-Sent Events; read via fetch's ReadableStream
// since EventSource only supports GET)
// ---------------------------------------------------------------------------
export interface StreamHandlers {
  onStatus?: (phase: string) => void;
  onSources?: (standaloneQuestion: string, sources: Source[]) => void;
  onToken?: (text: string) => void;
  onDone?: (answer: string, timingsMs: Record<string, number>) => void;
  onError?: (error: unknown) => void;
}

export async function streamMessage(
  id: string,
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/conversations/${id}/messages/stream`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (error) {
    handlers.onError?.(error);
    return;
  }

  if (res.status === 401) onUnauthorized?.();
  if (!res.ok || !res.body) {
    handlers.onError?.(new ApiError(res.status, `Stream failed (${res.status})`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE frames are separated by a blank line.
      let sep = buffer.indexOf("\n\n");
      while (sep !== -1) {
        dispatchFrame(buffer.slice(0, sep), handlers);
        buffer = buffer.slice(sep + 2);
        sep = buffer.indexOf("\n\n");
      }
    }
  } catch (error) {
    if ((error as { name?: string }).name !== "AbortError") handlers.onError?.(error);
  }
}

function dispatchFrame(frame: string, handlers: StreamHandlers): void {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return;

  let data: Record<string, unknown>;
  try {
    data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
  } catch {
    return;
  }

  switch (event) {
    case "status":
      handlers.onStatus?.(String(data.phase ?? ""));
      break;
    case "sources":
      handlers.onSources?.(
        String(data.standalone_question ?? ""),
        (data.sources as Source[] | undefined) ?? [],
      );
      break;
    case "token":
      handlers.onToken?.(String(data.text ?? ""));
      break;
    case "done":
      handlers.onDone?.(
        String(data.answer ?? ""),
        (data.timings_ms as Record<string, number> | undefined) ?? {},
      );
      break;
  }
}
