import { useEffect, useState } from "react";
import { useAuth } from "./auth/AuthContext";
import AdminConsole from "./components/AdminConsole";
import Chat from "./components/Chat";
import Login from "./components/Login";

type View = "chat" | "admin";

export default function App() {
  const { user, loading, logout } = useAuth();
  const [view, setView] = useState<View>("chat");
  const [model, setModel] = useState("");

  useEffect(() => {
    fetch("/api/meta")
      .then((r) => r.json())
      .then((d) => setModel(d.answer_model ?? ""))
      .catch(() => setModel(""));
  }, []);

  // Every login (or user switch) lands on the chat — so a technician after an admin session
  // never sees a stale admin view.
  useEffect(() => {
    setView("chat");
  }, [user?.email]);

  if (loading) return <div className="app-loading">Loading…</div>;
  if (!user) return <Login />;

  // Belt-and-suspenders: only admins can ever see the admin view.
  const showAdmin = user.role === "admin" && view === "admin";

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">J</span>
          <div className="brand-text">
            <strong>Jensen AI Technical Assistant</strong>
            <span className="brand-sub">Field Service Industrial Laundry Equipment</span>
          </div>
        </div>

        {/* Admins get Chat/Admin tabs; technicians land straight in the chat (no tabs). */}
        {user.role === "admin" && (
          <nav className="app-nav">
            <button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}>
              Chat
            </button>
            <button className={view === "admin" ? "active" : ""} onClick={() => setView("admin")}>
              Admin
            </button>
          </nav>
        )}

        <div className="header-meta">
          {model && (
            <span className="model-pill" title="Local model answering (via Ollama)">
              <span className="model-dot" /> AI Model: {model}
            </span>
          )}
          <span className="user-chip">
            Username: <b>{user.email}</b> · Role: <b>{user.role}</b>
          </span>
          <button className="logout-btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      {showAdmin ? <AdminConsole /> : <Chat />}
    </div>
  );
}
