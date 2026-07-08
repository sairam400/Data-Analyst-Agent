import styles from "./TracePanel.module.css";

function StepArgs({ tool, args }) {
  if (tool === "run_sql" && typeof args.query === "string") {
    return <pre className={styles.code}>{args.query}</pre>;
  }
  if (tool === "run_python" && typeof args.code === "string") {
    return <pre className={styles.code}>{args.code}</pre>;
  }
  return <pre className={styles.code}>{JSON.stringify(args)}</pre>;
}

function StepObservation({ step }) {
  if (step.error) {
    return <div className={styles.errorText}>error: {step.error}</div>;
  }
  if (step.tool === "make_chart" && step.observation?.image_base64) {
    return (
      <img
        className={styles.chartImage}
        src={`data:image/png;base64,${step.observation.image_base64}`}
        alt={step.observation.title || "chart"}
      />
    );
  }
  return <div className={styles.observation}>{JSON.stringify(step.observation)}</div>;
}

export default function TracePanel({ trace }) {
  const toolSteps = trace.steps.filter((s) => s.type === "tool");

  return (
    <details className={styles.trace}>
      <summary>
        agent trace &middot; {toolSteps.length} tool call{toolSteps.length === 1 ? "" : "s"}
        {trace.retries > 0 && (
          <span className={styles.retryBadge}>
            {trace.retries} retr{trace.retries === 1 ? "y" : "ies"}
          </span>
        )}
        &middot; {trace.elapsed_seconds}s
      </summary>
      <div className={styles.rail}>
        {trace.steps.map((step, i) => {
          if (step.type === "final") {
            return (
              <div key={i} className={`${styles.step} ${styles.finalStep}`}>
                <div className={styles.stepNum}>&#10003;</div>
                <div className={styles.stepBody}>
                  <div className={styles.finalAnswer}>{step.answer}</div>
                </div>
              </div>
            );
          }
          return (
            <div key={i} className={`${styles.step} ${step.error ? styles.errorStep : ""}`}>
              <div className={styles.stepNum}>{i + 1}</div>
              <div className={styles.stepBody}>
                <span className={styles.toolChip}>{step.tool}</span>
                <StepArgs tool={step.tool} args={step.args} />
                <StepObservation step={step} />
              </div>
            </div>
          );
        })}
      </div>
    </details>
  );
}
