import { useState, type KeyboardEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import type { ConversationSummary } from "../api";
import { Logo } from "./Logo";
import { CheckIcon, CloseIcon, LogoutIcon, PencilIcon, PlusIcon, TrashIcon } from "./icons";

interface SidebarProps {
  conversations: ConversationSummary[];
  activeId: string | undefined;
  busy: boolean;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

export function Sidebar({
  conversations,
  activeId,
  busy,
  onNew,
  onSelect,
  onRename,
  onDelete,
}: SidebarProps) {
  const { user, logout } = useAuth();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [confirmId, setConfirmId] = useState<string | null>(null);

  function startEdit(c: ConversationSummary) {
    setConfirmId(null);
    setEditingId(c.id);
    setDraft(c.title);
  }

  function commitEdit() {
    if (editingId) {
      const title = draft.trim();
      if (title) onRename(editingId, title);
    }
    setEditingId(null);
  }

  function onEditKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") commitEdit();
    else if (e.key === "Escape") setEditingId(null);
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-edge bg-panel">
      <div className="flex items-center justify-between px-4 py-4">
        <Logo />
      </div>

      <div className="px-3">
        <button
          onClick={onNew}
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-accent/40 bg-accent/10 px-3 py-2.5 text-sm font-medium text-accent-2 transition hover:bg-accent/20 disabled:opacity-50"
        >
          <PlusIcon width={16} height={16} />
          New chat
        </button>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto px-2 pb-2">
        <div className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-fog-2">
          Conversations
        </div>
        {conversations.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm text-fog-2">No conversations yet.</p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {conversations.map((c) => {
              const active = c.id === activeId;
              if (editingId === c.id) {
                return (
                  <li key={c.id}>
                    <input
                      autoFocus
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={onEditKey}
                      onBlur={commitEdit}
                      className="w-full rounded-lg border border-accent bg-panel-3 px-3 py-2 text-sm text-white outline-none"
                    />
                  </li>
                );
              }
              return (
                <li key={c.id} className="group relative">
                  <button
                    onClick={() => onSelect(c.id)}
                    className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition ${
                      active
                        ? "bg-panel-2 text-white"
                        : "text-fog hover:bg-panel-2/60 hover:text-white"
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r bg-accent" />
                    )}
                    <span className="truncate pr-14">{c.title}</span>
                  </button>

                  {confirmId === c.id ? (
                    <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-1">
                      <button
                        title="Confirm delete"
                        onClick={() => {
                          onDelete(c.id);
                          setConfirmId(null);
                        }}
                        className="rounded p-1 text-red-300 hover:bg-red-500/20"
                      >
                        <CheckIcon width={15} height={15} />
                      </button>
                      <button
                        title="Cancel"
                        onClick={() => setConfirmId(null)}
                        className="rounded p-1 text-fog hover:bg-panel-3"
                      >
                        <CloseIcon width={15} height={15} />
                      </button>
                    </div>
                  ) : (
                    <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-0.5 opacity-0 transition group-hover:opacity-100">
                      <button
                        title="Rename"
                        onClick={() => startEdit(c)}
                        className="rounded p-1 text-fog hover:bg-panel-3 hover:text-white"
                      >
                        <PencilIcon width={15} height={15} />
                      </button>
                      <button
                        title="Delete"
                        onClick={() => setConfirmId(c.id)}
                        className="rounded p-1 text-fog hover:bg-panel-3 hover:text-red-300"
                      >
                        <TrashIcon width={15} height={15} />
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="border-t border-edge p-3">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-panel-3 text-xs font-semibold text-accent-2">
            {(user?.email ?? "?").slice(0, 1).toUpperCase()}
          </div>
          <span className="flex-1 truncate text-sm text-fog" title={user?.email}>
            {user?.email}
          </span>
          <button
            title="Sign out"
            onClick={logout}
            className="rounded-lg p-2 text-fog transition hover:bg-panel-3 hover:text-white"
          >
            <LogoutIcon width={16} height={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
