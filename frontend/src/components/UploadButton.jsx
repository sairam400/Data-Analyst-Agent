import { useState } from "react";
import { uploadCsv } from "../api.js";
import styles from "./UploadButton.module.css";

export default function UploadButton({ onUploaded }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  async function handleChange(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setError(null);
    setStatus(`uploading ${file.name}...`);
    try {
      const result = await uploadCsv(file);
      setStatus(`loaded ${result.row_count} rows into "${result.table}"`);
      onUploaded?.(result);
    } catch (err) {
      setStatus(null);
      setError(err.message);
    }
  }

  return (
    <div className={styles.wrap}>
      <label className={styles.label}>
        Upload CSV
        <input type="file" accept=".csv" onChange={handleChange} hidden />
      </label>
      {status && <span className={styles.status}>{status}</span>}
      {error && <span className={styles.statusError}>{error}</span>}
    </div>
  );
}
