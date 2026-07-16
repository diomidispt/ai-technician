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

  if (loading) return <div className="app-loading">Loading…</div>;
  if (!user) return <Login />;

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">J</span>
          <div className="brand-text">
            <strong>Jensen Technical Assistant</strong>
            <span className="brand-sub">Field service · industrial laundry equipment</span>
          </div>
        </div>

        <nav className="app-nav">
          <button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}>
            Chat
          </button>
          {user.role === "admin" && (
            <button className={view === "admin" ? "active" : ""} onClick={() => setView("admin")}>
              Admin
            </button>
          )}
        </nav>

        <div className="header-meta">
          {model && (
            <span className="model-pill" title="Local model answering (via Ollama)">
              <span className="model-dot" /> {model}
            </span>
          )}
          <span className="user-chip">
            {user.email} · <b>{user.role}</b>
          </span>
          <button className="logout-btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      {view === "chat" ? <Chat /> : <AdminConsole />}
    </div>
  );
}
