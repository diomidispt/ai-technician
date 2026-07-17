import { useCallback, useEffect, useRef, useState } from "react";
import {
  type AdminUser,
  type AuditEntry,
  type LibraryDoc,
  createUser,
  deleteDocument,
  deleteUser,
  listAudit,
  listDocuments,
  listUsers,
  updateUser,
  uploadDocument,
} from "../api/admin";

type Tab = "users" | "documents" | "audit";

export default function AdminConsole() {
  const [tab, setTab] = useState<Tab>("users");
  return (
    <div className="admin">
      <div className="admin-tabs">
        {(["users", "documents", "audit"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "users" ? "Users" : t === "documents" ? "Library" : "Audit log"}
          </button>
        ))}
      </div>
      <div className="admin-body">
        {tab === "users" && <UsersPanel />}
        {tab === "documents" && <DocumentsPanel />}
        {tab === "audit" && <AuditPanel />}
      </div>
    </div>
  );
}

function useAsyncError() {
  const [error, setError] = useState("");
  const wrap = useCallback(async (fn: () => Promise<void>) => {
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);
  return { error, wrap };
}

// ---------------- Users ----------------
function UsersPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("technician");
  const [expires, setExpires] = useState("");
  const { error, wrap } = useAsyncError();

  // Filters
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const refresh = useCallback(() => wrap(async () => setUsers(await listUsers())), [wrap]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  const shown = users.filter(
    (u) =>
      u.email.toLowerCase().includes(q.toLowerCase()) &&
      (roleFilter === "all" || u.role === roleFilter) &&
      (statusFilter === "all" || (statusFilter === "active" ? u.is_active : !u.is_active)),
  );

  const onCreate = () =>
    wrap(async () => {
      await createUser({
        email,
        password,
        role,
        access_expires: expires ? new Date(expires).toISOString() : null,
      });
      setEmail("");
      setPassword("");
      setExpires("");
      await refresh();
    });

  return (
    <div>
      <h3>Users &amp; access</h3>
      <p className="admin-note">
        Mirrors Cognito: roles, instant disable (revocation), and an access-expiry date.
      </p>
      {error && <p className="login-error">{error}</p>}

      <div className="create-user">
        <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          placeholder="password"
          type="text"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="technician">technician</option>
          <option value="admin">admin</option>
        </select>
        <input
          type="date"
          title="Access expiry (optional)"
          value={expires}
          onChange={(e) => setExpires(e.target.value)}
        />
        <button onClick={onCreate} disabled={!email || !password}>
          Add user
        </button>
      </div>

      <div className="admin-filters">
        <input placeholder="Search email…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="all">All roles</option>
          <option value="admin">admin</option>
          <option value="technician">technician</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="active">active</option>
          <option value="disabled">disabled</option>
        </select>
        <span className="filter-count">
          {shown.length} / {users.length}
        </span>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Expires</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {shown.map((u) => (
            <tr key={u.id} className={u.is_active ? "" : "disabled-row"}>
              <td>{u.email}</td>
              <td>{u.role}</td>
              <td>
                {u.is_active ? "active" : "disabled"}
                {u.must_change_password && <span className="reset-badge">must reset</span>}
              </td>
              <td>{u.access_expires ? u.access_expires.slice(0, 10) : "—"}</td>
              <td className="row-actions">
                <button
                  onClick={() =>
                    wrap(async () => {
                      await updateUser(u.id, { is_active: !u.is_active });
                      await refresh();
                    })
                  }
                >
                  {u.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  onClick={() =>
                    wrap(async () => {
                      const temp = window.prompt(
                        `Set a temporary password for ${u.email}.\nThey'll be forced to change it at next sign-in.`,
                      );
                      if (!temp) return;
                      await updateUser(u.id, { password: temp, must_change_password: true });
                      await refresh();
                    })
                  }
                >
                  Reset password
                </button>
                <button
                  className="danger"
                  onClick={() =>
                    wrap(async () => {
                      await deleteUser(u.id);
                      await refresh();
                    })
                  }
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------- Documents ----------------
function DocumentsPanel() {
  const [docs, setDocs] = useState<LibraryDoc[]>([]);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const { error, wrap } = useAsyncError();

  const refresh = useCallback(() => wrap(async () => setDocs(await listDocuments())), [wrap]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  const shown = docs.filter((d) => d.filename.toLowerCase().includes(q.toLowerCase()));

  const onUpload = () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setStatus(`Uploading & ingesting “${file.name}” — this can take a minute…`);
    wrap(async () => {
      const doc = await uploadDocument(file);
      setStatus(`Ingested “${doc.filename}” (${doc.chunks} chunks).`);
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    }).finally(() => setTimeout(() => setStatus(""), 6000));
  };

  return (
    <div>
      <h3>Document library</h3>
      <p className="admin-note">
        Upload PDF manuals — they’re parsed, chunked, embedded, and searchable. The local
        stand-in for the S3 / Drive drop.
      </p>
      {error && <p className="login-error">{error}</p>}

      <div className="upload-row">
        <input ref={fileRef} type="file" accept="application/pdf" />
        <button onClick={onUpload}>Upload &amp; ingest</button>
      </div>
      {status && <p className="admin-status">{status}</p>}

      <div className="admin-filters">
        <input placeholder="Search filename…" value={q} onChange={(e) => setQ(e.target.value)} />
        <span className="filter-count">
          {shown.length} / {docs.length}
        </span>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Chunks</th>
            <th>Added</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {shown.map((d) => (
            <tr key={d.id}>
              <td>{d.filename}</td>
              <td>{d.chunks}</td>
              <td>{d.created_at.slice(0, 10)}</td>
              <td className="row-actions">
                <button
                  className="danger"
                  onClick={() =>
                    wrap(async () => {
                      await deleteDocument(d.id);
                      await refresh();
                    })
                  }
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------- Audit ----------------
function AuditPanel() {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [q, setQ] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [userFilter, setUserFilter] = useState("all");
  const { error, wrap } = useAsyncError();
  const refresh = useCallback(() => wrap(async () => setRows(await listAudit())), [wrap]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  const users = Array.from(new Set(rows.map((r) => r.user_email))).sort();
  const shown = rows.filter(
    (r) =>
      (r.question.toLowerCase().includes(q.toLowerCase()) ||
        r.user_email.toLowerCase().includes(q.toLowerCase())) &&
      (sourceFilter === "all" || r.source === sourceFilter) &&
      (userFilter === "all" || r.user_email === userFilter),
  );

  return (
    <div>
      <h3>Query audit log</h3>
      <p className="admin-note">Who asked what, and whether it was answered from the library or the web.</p>
      {error && <p className="login-error">{error}</p>}

      <div className="admin-filters">
        <input
          placeholder="Search question or user…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
          <option value="all">All sources</option>
          <option value="internal">internal</option>
          <option value="web">web</option>
          <option value="none">none</option>
        </select>
        <select value={userFilter} onChange={(e) => setUserFilter(e.target.value)}>
          <option value="all">All users</option>
          {users.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
        <button className="refresh-btn" onClick={refresh}>
          Refresh
        </button>
        <span className="filter-count">
          {shown.length} / {rows.length}
        </span>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>User</th>
            <th>Source</th>
            <th>Question</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i}>
              <td className="mono">{r.created_at.slice(0, 19).replace("T", " ")}</td>
              <td>{r.user_email}</td>
              <td>
                <span className={`src-tag src-${r.source}`}>{r.source}</span>
              </td>
              <td>{r.question}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
