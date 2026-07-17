// Per-user chat-history API (all scoped to the signed-in user by the backend).
import { apiJson } from "./client";
import type { AnswerSource, Citation } from "./chat";

export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string;
}

export interface StoredMessage {
  role: "user" | "assistant";
  content: string;
  source?: AnswerSource | null;
  citations?: Citation[] | null;
}

export interface ConversationDetail {
  id: number;
  title: string;
  messages: StoredMessage[];
}

export const listConversations = () => apiJson<ConversationSummary[]>("/api/conversations");

export const getConversation = (id: number) =>
  apiJson<ConversationDetail>(`/api/conversations/${id}`);

export const deleteConversation = (id: number) =>
  apiJson<void>(`/api/conversations/${id}`, { method: "DELETE" });
