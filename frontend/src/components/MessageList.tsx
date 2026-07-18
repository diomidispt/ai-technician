import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import type { UiMessage } from "./Chat";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages }: { messages: UiMessage[] }) {
  const { t } = useI18n();
  const suggestions = [t.suggestion1, t.suggestion2, t.suggestion3];
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <h1>{t.emptyTitle}</h1>
          <p>{t.emptyDesc}</p>
          <ul className="suggestions">
            {suggestions.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
