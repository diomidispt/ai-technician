// Reads the text / error code off a photographed equipment display (local vision model, $0).
import { apiFetch } from "./client";

export async function extractImageText(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch("/api/vision/extract", { method: "POST", body: form });
  if (!res.ok) {
    let detail = `Couldn't read the image (${res.status})`;
    try {
      detail = (await res.json())?.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const data = (await res.json()) as { text: string };
  return data.text;
}
