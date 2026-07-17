import type { ConversationSummary } from "../api/conversations";

interface Props {
  conversations: ConversationSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onDelete: (id: number) => void;
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d`;
  return new Date(iso).toLocaleDateString();
}

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  return (
    <aside className="conv-sidebar">
      <button className="conv-new" onClick={onNew}>
        + New chat
      </button>
      <div className="conv-list">
        {conversations.length === 0 ? (
          <p className="conv-empty">No conversations yet.</p>
        ) : (
          conversations.map((c) => (
            <div
              key={c.id}
              className={`conv-item ${c.id === activeId ? "active" : ""}`}
              onClick={() => onSelect(c.id)}
              title={c.title}
            >
              <span className="conv-title">{c.title}</span>
              <span className="conv-time">{relativeTime(c.updated_at)}</span>
              <button
                className="conv-del"
                aria-label="Delete conversation"
                title="Delete"
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
  );
}
