// Admin console API calls (all require an admin token; the backend enforces it).
import { apiFetch, apiJson, getToken } from "./client";

export interface AdminUser {
  id: number;
  email: string;
  role: "admin" | "technician";
  is_active: boolean;
  access_expires: string | null;
}

export interface LibraryDoc {
  id: number;
  filename: string;
  chunks: number;
  created_at: string;
}

export interface AuditEntry {
  user_email: string;
  question: string;
  source: string;
  created_at: string;
}

export const listUsers = () => apiJson<AdminUser[]>("/api/admin/users");

export const createUser = (body: {
  email: string;
  password: string;
  role: string;
  access_expires: string | null;
}) => apiJson<AdminUser>("/api/admin/users", { method: "POST", body: JSON.stringify(body) });

export const updateUser = (id: number, body: Record<string, unknown>) =>
  apiJson<AdminUser>(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) });

export const deleteUser = (id: number) =>
  apiJson<void>(`/api/admin/users/${id}`, { method: "DELETE" });

export const listDocuments = () => apiJson<LibraryDoc[]>("/api/admin/documents");

export const deleteDocument = (id: number) =>
  apiJson<void>(`/api/admin/documents/${id}`, { method: "DELETE" });

export const listAudit = () => apiJson<AuditEntry[]>("/api/admin/audit?limit=100");

/** Upload a PDF (multipart). Uses apiFetch directly so we don't set a JSON content-type. */
export async function uploadDocument(file: File): Promise<LibraryDoc> {
  const form = new FormData();
  form.append("file", file);
  const token = getToken();
  const res = await apiFetch("/api/admin/documents", {
    method: "POST",
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) {
    let detail = `Upload failed (${res.status})`;
    try {
      detail = (await res.json())?.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as LibraryDoc;
}
