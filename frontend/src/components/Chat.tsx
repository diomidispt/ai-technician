import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat, type AnswerSource, type ChatMessage, type Citation } from "../api/chat";
import {
  type ConversationSummary,
  deleteConversation,
  getConversation,
  listConversations,
} from "../api/conversations";
import { useI18n } from "../i18n";
import Composer from "./Composer";
import ConversationSidebar from "./ConversationSidebar";
import MessageList from "./MessageList";

export interface UiMessage extends ChatMessage {
  id: string;
  citations?: Citation[];
  source?: AnswerSource;
  streaming?: boolean;
}

let idCounter = 0;
const nextId = () => `m${++idCounter}`;

export default function Chat() {
  const { t } = useI18n();
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false); // mobile drawer
  const abortRef = useRef<AbortController | null>(null);

  const refreshList = useCallback(() => {
    listConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  const newChat = useCallback(() => {
    if (busy) return;
    setConversationId(null);
    setMessages([]);
    setSidebarOpen(false);
  }, [busy]);

  const selectConversation = useCallback(
    async (id: number) => {
      if (busy || id === conversationId) return;
      setSidebarOpen(false);
      try {
        const conv = await getConversation(id);
        setConversationId(conv.id);
        setMessages(
          conv.messages.map((m) => ({
            id: nextId(),
            role: m.role,
            content: m.content,
            source: m.source ?? undefined,
            citations: m.citations ?? undefined,
          })),
        );
      } catch {
        /* ignore — likely deleted elsewhere */
      }
    },
    [busy, conversationId],
  );

  const removeConversation = useCallback(
    async (id: number) => {
      try {
        await deleteConversation(id);
      } catch {
        /* ignore */
      }
      if (id === conversationId) {
        setConversationId(null);
        setMessages([]);
      }
      refreshList();
    },
    [conversationId, refreshList],
  );

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
        conversationId,
        {
          onToken: (delta) => patch((m) => ({ ...m, content: m.content + delta })),
          onDone: (source, citations, newId) => {
            patch((m) => ({ ...m, source, citations, streaming: false }));
            if (newId && newId !== conversationId) setConversationId(newId);
            refreshList();
          },
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
    [busy, messages, conversationId, refreshList],
  );

  return (
    <div className="chat-layout">
      <ConversationSidebar
        conversations={conversations}
        activeId={conversationId}
        onSelect={selectConversation}
        onNew={newChat}
        onDelete={removeConversation}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="chat">
        <div className="chat-mobilebar">
          <button
            className="sidebar-toggle"
            aria-label={t.showConversations}
            onClick={() => setSidebarOpen(true)}
          >
            ☰
          </button>
          <span className="chat-mobilebar-title">{t.chatsTitle}</span>
        </div>
        <MessageList messages={messages} />
        <Composer onSend={send} disabled={busy} />
      </main>
    </div>
  );
}
