import { useState, type KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export default function Composer({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  // Enter sends; Shift+Enter inserts a newline.
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="composer">
      <div className="composer-inner">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask a troubleshooting question…"
          rows={1}
          autoFocus
        />
        <button onClick={submit} disabled={disabled || !text.trim()} aria-label="Send">
          ↑
        </button>
      </div>
      <p className="composer-hint">
        Enter to send · Shift+Enter for a new line · answers come from ingested manuals, with citations
      </p>
    </div>
  );
}
