// Client for POST /api/chat — consumes the backend SSE contract:
//   event: token   data: {"delta": "..."}   (zero or more, in order)
//   event: done    data: {"citations": [...]} (terminal)
//
// This mirrors the backend contract in backend/app/api/chat.py. When RAG lands the
// backend yields real deltas + citations; this parser does not change.

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface Citation {
  manual: string;
  page?: string | number;
  section?: string;
}

interface StreamHandlers {
  onToken: (delta: string) => void;
  onDone: (citations: Citation[]) => void;
  onError: (error: Error) => void;
}

export async function streamChat(
  messages: ChatMessage[],
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ messages }),
      signal,
    });
  } catch (err) {
    handlers.onError(err instanceof Error ? err : new Error(String(err)));
    return;
  }

  if (!response.ok || !response.body) {
    handlers.onError(new Error(`Request failed: ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      // Normalise CRLF -> LF: sse-starlette emits `\r\n` line endings, so events are
      // separated by `\r\n\r\n`. Without this, a `\n\n` split never matches and no
      // token is ever surfaced (the UI would hang on the typing indicator).
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n");

      // SSE events are separated by a blank line.
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        dispatchEvent(rawEvent, handlers);
      }
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") {
      handlers.onError(err instanceof Error ? err : new Error(String(err)));
    }
  }
}

function dispatchEvent(rawEvent: string, handlers: StreamHandlers): void {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  const data = dataLines.join("\n");
  if (!data) return;

  try {
    const parsed = JSON.parse(data);
    if (event === "token" && typeof parsed.delta === "string") {
      handlers.onToken(parsed.delta);
    } else if (event === "done") {
      handlers.onDone(parsed.citations ?? []);
    }
  } catch {
    // Ignore malformed frames — the stream keeps going.
  }
}
