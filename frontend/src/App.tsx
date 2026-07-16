import { useEffect, useState } from "react";
import Chat from "./components/Chat";

export default function App() {
  const [model, setModel] = useState<string>("");

  useEffect(() => {
    fetch("/api/meta")
      .then((r) => r.json())
      .then((d) => setModel(d.answer_model ?? ""))
      .catch(() => setModel(""));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">J</span>
          <div className="brand-text">
            <strong>Jensen Technical Assistant</strong>
            <span className="brand-sub">Field service · industrial laundry equipment</span>
          </div>
        </div>
        <div className="header-meta">
          {model && (
            <span className="model-pill" title="Local model answering (via Ollama)">
              <span className="model-dot" /> {model}
            </span>
          )}
          <span className="demo-badge">Answers from your manuals · with citations</span>
        </div>
      </header>
      <Chat />
    </div>
  );
}
