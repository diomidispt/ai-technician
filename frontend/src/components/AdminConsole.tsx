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
import { roleLabel, useI18n } from "../i18n";

type Tab = "users" | "documents" | "audit";

export default function AdminConsole() {
  const { t } = useI18n();
  const [tab, setTab] = useState<Tab>("users");
  return (
    <div className="admin">
      <div className="admin-tabs">
        {(["users", "documents", "audit"] as Tab[]).map((key) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {key === "users" ? t.tabUsers : key === "documents" ? t.tabLibrary : t.tabAudit}
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
  const { t } = useI18n();
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
      <h3>{t.usersHeading}</h3>
      <p className="admin-note">{t.usersNote}</p>
      {error && <p className="login-error">{error}</p>}

      <div className="create-user">
        <input
          placeholder={t.emailPlaceholder}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          placeholder={t.passwordPlaceholder}
          type="text"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="technician">{t.roleTechnician}</option>
          <option value="admin">{t.roleAdmin}</option>
        </select>
        <input
          type="date"
          title={t.accessExpiryTitle}
          value={expires}
          onChange={(e) => setExpires(e.target.value)}
        />
        <button onClick={onCreate} disabled={!email || !password}>
          {t.addUser}
        </button>
      </div>

      <div className="admin-filters">
        <input placeholder={t.searchEmail} value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="all">{t.allRoles}</option>
          <option value="admin">{t.roleAdmin}</option>
          <option value="technician">{t.roleTechnician}</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">{t.allStatuses}</option>
          <option value="active">{t.statusActive}</option>
          <option value="disabled">{t.statusDisabled}</option>
        </select>
        <span className="filter-count">
          {shown.length} / {users.length}
        </span>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>{t.colEmail}</th>
            <th>{t.colRole}</th>
            <th>{t.colStatus}</th>
            <th>{t.colExpires}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {shown.map((u) => (
            <tr key={u.id} className={u.is_active ? "" : "disabled-row"}>
              <td>{u.email}</td>
              <td>{roleLabel(u.role, t)}</td>
              <td>
                {u.is_active ? t.statusActive : t.statusDisabled}
                {u.must_change_password && <span className="reset-badge">{t.mustReset}</span>}
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
                  {u.is_active ? t.disable : t.enable}
                </button>
                <button
                  onClick={() =>
                    wrap(async () => {
                      const temp = window.prompt(
                        `${t.resetPromptTitle} ${u.email}.\n${t.resetPromptHint}`,
                      );
                      if (!temp) return;
                      await updateUser(u.id, { password: temp, must_change_password: true });
                      await refresh();
                    })
                  }
                >
                  {t.resetPassword}
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
                  {t.delete}
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
  const { t } = useI18n();
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
    setStatus(`${t.uploadingPrefix} “${file.name}” ${t.uploadingSuffix}`);
    wrap(async () => {
      const doc = await uploadDocument(file);
      setStatus(`${t.ingestedPrefix} “${doc.filename}” (${doc.chunks} ${t.chunksWord}).`);
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    }).finally(() => setTimeout(() => setStatus(""), 6000));
  };

  return (
    <div>
      <h3>{t.docsHeading}</h3>
      <p className="admin-note">{t.docsNote}</p>
      {error && <p className="login-error">{error}</p>}

      <div className="upload-row">
        <input ref={fileRef} type="file" accept="application/pdf" />
        <button onClick={onUpload}>{t.uploadIngest}</button>
      </div>
      {status && <p className="admin-status">{status}</p>}

      <div className="admin-filters">
        <input placeholder={t.searchFilename} value={q} onChange={(e) => setQ(e.target.value)} />
        <span className="filter-count">
          {shown.length} / {docs.length}
        </span>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>{t.colFile}</th>
            <th>{t.colChunks}</th>
            <th>{t.colAdded}</th>
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
                  {t.delete}
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
  const { t } = useI18n();
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [q, setQ] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [userFilter, setUserFilter] = useState("all");
  const [refreshing, setRefreshing] = useState(false);
  const { error, wrap } = useAsyncError();
  const refresh = useCallback(
    () =>
      wrap(async () => {
        setRefreshing(true);
        try {
          setRows(await listAudit());
        } finally {
          setRefreshing(false);
        }
      }),
    [wrap],
  );
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
      <h3>{t.auditHeading}</h3>
      <p className="admin-note">{t.auditNote}</p>
      {error && <p className="login-error">{error}</p>}

      <div className="admin-filters">
        <input
          placeholder={t.searchQuestionUser}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
          <option value="all">{t.allSources}</option>
          <option value="internal">internal</option>
          <option value="web">web</option>
          <option value="chat">chat</option>
        </select>
        <select value={userFilter} onChange={(e) => setUserFilter(e.target.value)}>
          <option value="all">{t.allUsers}</option>
          {users.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
        <button className="refresh-btn" onClick={refresh} disabled={refreshing}>
          {refreshing ? "…" : t.refresh}
        </button>
        <span className="filter-count">
          {shown.length} / {rows.length}
        </span>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>{t.colTime}</th>
            <th>{t.colUser}</th>
            <th>{t.colSource}</th>
            <th>{t.colQuestion}</th>
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
