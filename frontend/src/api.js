const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseErrorDetail(res) {
  const body = await res.json().catch(() => ({}));
  return body.detail || `request failed with status ${res.status}`;
}

export async function askQuestion(question) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function uploadCsv(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function getSchema() {
  const res = await fetch(`${API_BASE}/schema`);
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}
