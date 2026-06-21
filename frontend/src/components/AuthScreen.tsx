import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api";
import { Logo } from "./Logo";

function humanize(err: unknown, isRegister: boolean): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "That email is already registered.";
    if (err.status === 401) return "Invalid email or password.";
    if (err.status === 422)
      return "Enter a valid email and a password of at least 8 characters.";
    return err.message;
  }
  return isRegister ? "Could not create your account." : "Could not sign you in.";
}

export function AuthScreen({ mode }: { mode: "login" | "register" }) {
  const isRegister = mode === "register";
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isRegister) await register(email, password);
      else await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(humanize(err, isRegister));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative grid h-full place-items-center overflow-hidden px-4">
      {/* Ambient accent glow behind the card. */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[420px] w-[620px] -translate-x-1/2 rounded-full bg-accent/20 blur-[120px]" />

      <div className="relative w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <Logo />
          <div>
            <h1 className="text-xl font-semibold text-white">
              {isRegister ? "Create your account" : "Welcome back"}
            </h1>
            <p className="mt-1 text-sm text-fog">
              {isRegister
                ? "Sign up to chat with your industry reports."
                : "Sign in to continue to IndustryIQ."}
            </p>
          </div>
        </div>

        <form
          onSubmit={submit}
          className="rounded-2xl border border-edge bg-panel/80 p-6 shadow-2xl backdrop-blur"
        >
          <label className="mb-1.5 block text-xs font-medium text-fog">Email</label>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="mb-4 w-full rounded-lg border border-edge bg-panel-3 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-fog-2 focus:border-accent focus:ring-2 focus:ring-accent/30"
          />

          <label className="mb-1.5 block text-xs font-medium text-fog">Password</label>
          <input
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={isRegister ? "At least 8 characters" : "••••••••"}
            className="w-full rounded-lg border border-edge bg-panel-3 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-fog-2 focus:border-accent focus:ring-2 focus:ring-accent/30"
          />

          {error && (
            <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-5 w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-white transition hover:bg-accent-strong disabled:opacity-60"
          >
            {busy ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-fog">
          {isRegister ? "Already have an account? " : "New to IndustryIQ? "}
          <Link
            to={isRegister ? "/login" : "/register"}
            className="font-medium text-accent-2 hover:underline"
          >
            {isRegister ? "Sign in" : "Create one"}
          </Link>
        </p>
      </div>
    </div>
  );
}
