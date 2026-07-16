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

        {/* Citation slot — empty in phase 1. RAG answers will render manual/page here
            (CLAUDE.md golden rule: every answer carries citations). */}
        {message.citations && message.citations.length > 0 && (
          <div className="citations">
            {message.citations.map((c, i) => (
              <span className="citation" key={i}>
                {c.manual}
                {c.page ? ` · p.${c.page}` : ""}
                {c.section ? ` · ${c.section}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
