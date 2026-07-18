import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n";

interface Props {
  /** Forced mode: shown as a blocking screen after login when a reset is required. */
  forced?: boolean;
  /** Voluntary mode: called to close the panel. */
  onClose?: () => void;
}

export default function ChangePassword({ forced = false, onClose }: Props) {
  const { changePassword, logout } = useAuth();
  const { t } = useI18n();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (next !== confirm) {
      setError(t.cpMismatch);
      return;
    }
    setBusy(true);
    try {
      await changePassword(current, next);
      setDone(true);
      if (!forced && onClose) setTimeout(onClose, 900);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.cpFailed);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={forced ? "login" : "modal-overlay"}>
      <form className="login-card" onSubmit={onSubmit}>
        <div className="brand login-brand">
          <span className="brand-mark">J</span>
          <strong>{t.cpTitle}</strong>
        </div>
        <p className="login-sub">{forced ? t.cpForcedSubtitle : t.cpNormalSubtitle}</p>

        <label>
          {t.cpCurrent}
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label>
          {t.cpNew}
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            minLength={6}
            required
          />
        </label>
        <label>
          {t.cpConfirm}
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            minLength={6}
            required
          />
        </label>

        {error && <p className="login-error">{error}</p>}
        {done && <p className="admin-status">{t.cpUpdated}</p>}

        <button type="submit" className="login-btn" disabled={busy || done}>
          {busy ? t.cpUpdating : t.cpUpdate}
        </button>

        {forced ? (
          <button type="button" className="link-btn" onClick={logout}>
            {t.cpSignOutInstead}
          </button>
        ) : (
          onClose && (
            <button type="button" className="link-btn" onClick={onClose}>
              {t.cancel}
            </button>
          )
        )}
      </form>
    </div>
  );
}
