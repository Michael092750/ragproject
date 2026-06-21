import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as api from "../api";
import type { Me } from "../api";

interface AuthState {
  user: Me | null;
  loading: boolean; // true while the stored token is being validated on startup
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    api.clearToken();
    setUser(null);
  }, []);

  // On startup: a 401 anywhere clears the session; if we hold a token, validate
  // it by loading the current user (an expired token just bounces us to login).
  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      api.clearToken();
      setUser(null);
    });
    const token = api.getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => api.clearToken())
      .finally(() => setLoading(false));
    return () => api.setUnauthorizedHandler(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    api.setToken(await api.login(email, password));
    setUser(await api.me());
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    api.setToken(await api.register(email, password));
    setUser(await api.me());
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
