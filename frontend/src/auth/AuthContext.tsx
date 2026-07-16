import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { apiJson, clearToken, getToken, setToken } from "../api/client";

export interface User {
  email: string;
  role: "admin" | "technician";
}

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  // Validate an existing token on load (and pick up the user's role).
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    apiJson<User>("/api/auth/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  // Any 401 during use -> log out.
  useEffect(() => {
    const onUnauthorized = () => logout();
    window.addEventListener("auth:unauthorized", onUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", onUnauthorized);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    // Raw fetch (not apiFetch) so a bad-password 401 doesn't trigger a global logout.
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      let detail = "Login failed";
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    const data = (await res.json()) as { access_token: string; user: User };
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
