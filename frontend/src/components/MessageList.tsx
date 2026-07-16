import { useEffect, useRef } from "react";
import type { UiMessage } from "./Chat";
import MessageBubble from "./MessageBubble";

const SUGGESTIONS = [
  "Washer drum won't spin — where do I start?",
  "What does error code E14 mean on the ironer?",
  "Steam valve is leaking — safe shutdown steps?",
];

export default function MessageList({ messages }: { messages: UiMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <h1>How can I help with your service call?</h1>
          <p>
            Ask a troubleshooting question. Answers come from the manuals in your library —
            with source citations. If it's not in the manuals, I'll say so.
          </p>
          <ul className="suggestions">
            {SUGGESTIONS.map((s) => (
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
