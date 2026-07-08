import { useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import UploadButton from "./components/UploadButton.jsx";
import { askQuestion } from "./api.js";
import styles from "./App.module.css";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);

  async function handleAsk(question) {
    const id = crypto.randomUUID();
    setMessages((prev) => [...prev, { id, question, pending: true }]);
    setBusy(true);

    try {
      const trace = await askQuestion(question);
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, pending: false, trace } : m))
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, pending: false, error: err.message } : m))
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>AI Data Analyst Agent</h1>
          <p className={styles.subtitle}>Ask a question about your data in plain English.</p>
        </div>
        <UploadButton />
      </header>
      <main className={styles.main}>
        <ChatPanel messages={messages} onAsk={handleAsk} busy={busy} />
      </main>
    </div>
  );
}
