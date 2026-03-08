import { AnalysisResult } from "../types/analysis";
import { API_BASE } from "../constants";

export async function analyzeDrawing(
  file: File,
  age: string | null,
  context: string,
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);
  if (age) form.append("age", age);
  if (context) form.append("context", context);

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail || `HTTP ${res.status}`,
    );
  }

  return res.json() as Promise<AnalysisResult>;
}
