import Chat from "./components/Chat";

export default function App() {
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
        <span className="demo-badge">Answers from your manual library · with citations</span>
      </header>
      <Chat />
    </div>
  );
}
