import { useRef, useState, type KeyboardEvent } from "react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

// Recognition languages offered by the mic. Values are BCP-47 tags for the Web Speech API.
const VOICE_LANGS = [
  { code: "en-US", label: "EN" },
  { code: "el-GR", label: "EL" },
];

export default function Composer({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const [voiceLang, setVoiceLang] = useState("en-US");
  const { supported: voiceSupported, listening, start, stop } = useSpeechRecognition();
  // Text captured before dictation started, so interim results append rather than overwrite.
  const baseRef = useRef("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    if (listening) stop();
    onSend(trimmed);
    setText("");
    baseRef.current = "";
  };

  // Enter sends; Shift+Enter inserts a newline.
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const toggleMic = () => {
    if (listening) {
      stop();
      return;
    }
    baseRef.current = text ? text.trimEnd() + " " : "";
    start(voiceLang, {
      onInterim: (interim) => setText(baseRef.current + interim),
      onFinal: (final) => {
        baseRef.current = (baseRef.current + final).trimEnd() + " ";
        setText(baseRef.current);
      },
    });
  };

  return (
    <div className="composer">
      <div className="composer-inner">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={listening ? "Listening… speak now" : "Ask a troubleshooting question…"}
          rows={1}
          autoFocus
        />
        {voiceSupported && (
          <div className="voice-controls">
            <div className="voice-lang" role="group" aria-label="Voice language">
              {VOICE_LANGS.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  className={voiceLang === l.code ? "active" : ""}
                  onClick={() => setVoiceLang(l.code)}
                  disabled={listening}
                  title={`Recognize speech in ${l.label}`}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={`mic ${listening ? "recording" : ""}`}
              onClick={toggleMic}
              aria-label={listening ? "Stop dictation" : "Dictate your question"}
              title={listening ? "Stop dictation" : "Speak your question"}
            >
              {listening ? "■" : "🎤"}
            </button>
          </div>
        )}
        <button
          className="send"
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send"
        >
          ↑
        </button>
      </div>
      <p className="composer-hint">
        Enter to send · Shift+Enter for a new line
        {voiceSupported ? " · 🎤 to speak (EN/EL)" : ""} · answers come from ingested manuals,
        with citations
      </p>
    </div>
  );
}
