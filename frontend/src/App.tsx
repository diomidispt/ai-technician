import { useEffect, useState } from "react";
import { useAuth } from "./auth/AuthContext";
import AdminConsole from "./components/AdminConsole";
import ChangePassword from "./components/ChangePassword";
import Chat from "./components/Chat";
import Login from "./components/Login";
import { roleLabel, useI18n } from "./i18n";

type View = "chat" | "admin";

export default function App() {
  const { user, loading, logout } = useAuth();
  const { t, lang, toggle } = useI18n();
  const [view, setView] = useState<View>("chat");
  const [model, setModel] = useState("");
  const [showChangePw, setShowChangePw] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

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

  if (loading) return <div className="app-loading">{t.loading}</div>;
  if (!user) return <Login />;

  // Forced reset (fresh account / admin reset) blocks the app until the password is changed.
  if (user.must_change_password) return <ChangePassword forced />;

  // Belt-and-suspenders: only admins can ever see the admin view.
  const showAdmin = user.role === "admin" && view === "admin";

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">J</span>
          <div className="brand-text">
            <strong>{t.appName}</strong>
            <span className="brand-sub">{t.brandSub}</span>
          </div>
        </div>

        {/* Admins get Chat/Admin tabs; technicians land straight in the chat (no tabs). */}
        {user.role === "admin" && (
          <nav className="app-nav">
            <button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}>
              {t.navChat}
            </button>
            <button className={view === "admin" ? "active" : ""} onClick={() => setView("admin")}>
              {t.navAdmin}
            </button>
          </nav>
        )}

        {/* Right side: just the language toggle + a gear menu holding everything secondary. */}
        <div className="header-right">
          <button
            className="lang-toggle"
            onClick={toggle}
            title="Switch language / Αλλαγή γλώσσας"
            aria-label="Switch language"
          >
            🌐 {lang === "el" ? "EN" : "ΕΛ"}
          </button>

          <div className="gear-wrap">
            <button
              className="gear-btn"
              onClick={() => setMenuOpen((o) => !o)}
              aria-label="Menu"
              title="Menu"
            >
              ⚙
            </button>
            {menuOpen && (
              <>
                <div className="menu-backdrop" onClick={() => setMenuOpen(false)} />
                <div className="gear-menu">
                  <div className="gear-info">
                    <b>{user.email}</b>
                    <span className="gear-role">{roleLabel(user.role, t)}</span>
                  </div>
                  {model && (
                    <div className="gear-model">
                      {t.aiModel} {model}
                    </div>
                  )}
                  <div className="gear-sep" />
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      setShowChangePw(true);
                    }}
                  >
                    {t.changePassword}
                  </button>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      logout();
                    }}
                  >
                    {t.signOut}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {showAdmin ? <AdminConsole /> : <Chat />}
      {showChangePw && <ChangePassword onClose={() => setShowChangePw(false)} />}
    </div>
  );
}
