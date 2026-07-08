import { useEffect, useRef, useState } from "react";
import TracePanel from "./TracePanel.jsx";
import styles from "./ChatPanel.module.css";

export default function ChatPanel({ messages, onAsk, busy }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    onAsk(question);
    setInput("");
  }

  return (
    <div className={styles.chat}>
      <div className={styles.messages}>
        {messages.map((m) => (
          <div key={m.id} className={styles.message}>
            <div className={styles.question}>{m.question}</div>
            {m.pending && <div className={styles.pending}>thinking…</div>}
            {m.error && <div className={styles.errorAnswer}>{m.error}</div>}
            {m.trace && (
              <>
                <div className={styles.answer}>{m.trace.final_answer}</div>
                <TracePanel trace={m.trace} />
              </>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your data..."
          disabled={busy}
        />
        <button className={styles.submit} type="submit" disabled={busy || !input.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
