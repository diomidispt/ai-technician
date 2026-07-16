import ReactMarkdown from "react-markdown";
import type { UiMessage } from "./Chat";

export default function MessageBubble({ message }: { message: UiMessage }) {
  const isUser = message.role === "user";
  const showCursor = message.streaming && message.content.length === 0;

  return (
    <div className={`row ${isUser ? "row-user" : "row-assistant"}`}>
      <div className="avatar">{isUser ? "You" : "J"}</div>
      <div className="bubble">
        {showCursor ? (
          <span className="typing-dots" aria-label="Assistant is typing">
            <span />
            <span />
            <span />
          </span>
        ) : isUser ? (
          <p className="user-text">{message.content}</p>
        ) : (
          <div className="markdown">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.streaming && <span className="caret" />}
          </div>
        )}

        {/* Source badge: internal manuals vs an external web-search answer. */}
        {!isUser && !message.streaming && message.source === "web" && (
          <div className="source-badge web">🌐 From a web search — verify before acting</div>
        )}

        {/* Citations: manual+page for internal answers, title+link for web answers. */}
        {message.citations && message.citations.length > 0 && (
          <div className="citations">
            {message.citations.map((c, i) =>
              c.url ? (
                <a className="citation link" key={i} href={c.url} target="_blank" rel="noreferrer">
                  {c.title || c.url}
                </a>
              ) : (
                <span className="citation" key={i}>
                  {c.manual}
                  {c.page ? ` · p.${c.page}` : ""}
                  {c.section ? ` · ${c.section}` : ""}
                </span>
              ),
            )}
          </div>
        )}
      </div>
    </div>
  );
}
