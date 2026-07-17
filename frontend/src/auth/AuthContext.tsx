import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch, apiJson, clearToken, getToken, setToken } from "../api/client";

export interface User {
  email: string;
  role: "admin" | "technician";
  must_change_password: boolean;
}

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
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

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const res = await apiFetch("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (!res.ok) {
      let detail = "Could not change password";
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    // Clears the forced-reset flag so the app unblocks.
    setUser((u) => (u ? { ...u, must_change_password: false } : u));
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, changePassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
