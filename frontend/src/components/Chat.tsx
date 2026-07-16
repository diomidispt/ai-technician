import { useCallback, useRef, useState } from "react";
import { streamChat, type ChatMessage, type Citation } from "../api/chat";
import Composer from "./Composer";
import MessageList from "./MessageList";

export interface UiMessage extends ChatMessage {
  id: string;
  citations?: Citation[];
  streaming?: boolean;
}

let idCounter = 0;
const nextId = () => `m${++idCounter}`;

export default function Chat() {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (text: string) => {
      if (busy) return;

      const userMsg: UiMessage = { id: nextId(), role: "user", content: text };
      const assistantMsg: UiMessage = {
        id: nextId(),
        role: "assistant",
        content: "",
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setBusy(true);

      const history: ChatMessage[] = [...messages, userMsg].map(({ role, content }) => ({
        role,
        content,
      }));

      const controller = new AbortController();
      abortRef.current = controller;

      const patch = (fn: (m: UiMessage) => UiMessage) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantMsg.id ? fn(m) : m)));

      await streamChat(
        history,
        {
          onToken: (delta) => patch((m) => ({ ...m, content: m.content + delta })),
          onDone: (citations) => patch((m) => ({ ...m, citations, streaming: false })),
          onError: (err) =>
            patch((m) => ({
              ...m,
              content: m.content || `⚠️ ${err.message}`,
              streaming: false,
            })),
        },
        controller.signal,
      );

      setBusy(false);
      abortRef.current = null;
    },
    [busy, messages],
  );

  return (
    <main className="chat">
      <MessageList messages={messages} />
      <Composer onSend={send} disabled={busy} />
    </main>
  );
}
