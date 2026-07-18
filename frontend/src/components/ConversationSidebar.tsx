import type { ConversationSummary } from "../api/conversations";
import { useI18n, type Strings } from "../i18n";

interface Props {
  conversations: ConversationSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onDelete: (id: number) => void;
  /** Mobile drawer state (ignored on desktop, where the sidebar is always visible). */
  open?: boolean;
  onClose?: () => void;
}

function relativeTime(iso: string, t: Strings): string {
  const then = new Date(iso).getTime();
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return t.timeJustNow;
  if (mins < 60) return `${mins}${t.timeMin}`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}${t.timeHour}`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}${t.timeDay}`;
  return new Date(iso).toLocaleDateString();
}

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  open = false,
  onClose,
}: Props) {
  const { t } = useI18n();
  return (
    <>
      {open && <div className="conv-backdrop" onClick={onClose} />}
      <aside className={`conv-sidebar ${open ? "open" : ""}`}>
        <button className="conv-new" onClick={onNew}>
          {t.newChat}
        </button>
        <div className="conv-list">
          {conversations.length === 0 ? (
            <p className="conv-empty">{t.noConversations}</p>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                className={`conv-item ${c.id === activeId ? "active" : ""}`}
                onClick={() => onSelect(c.id)}
                title={c.title}
              >
                <span className="conv-title">{c.title}</span>
                <span className="conv-time">{relativeTime(c.updated_at, t)}</span>
                <button
                  className="conv-del"
                  aria-label={t.deleteConversation}
                  title={t.deleteConversation}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(c.id);
                  }}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}
