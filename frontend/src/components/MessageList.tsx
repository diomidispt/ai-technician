import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import type { UiMessage } from "./Chat";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages }: { messages: UiMessage[] }) {
  const { t } = useI18n();
  const containerRef = useRef<HTMLDivElement>(null);
  // Stick to the bottom only while the user is already near it — so they can scroll UP to read a
  // long answer mid-stream without being yanked back down.
  const stickRef = useRef(true);

  const onScroll = () => {
    const el = containerRef.current;
    if (el) stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  useEffect(() => {
    const el = containerRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <h1>{t.emptyTitle}</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list" ref={containerRef} onScroll={onScroll}>
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
    </div>
  );
}
