import { AnalysisResult } from "../types/analysis";
import { API_BASE } from "../constants";

export async function analyzeDrawing(
  file: File,
  age: string | null,
  context: string,
  mode: string = "auto",
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("mode", mode);
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

// ── История из PostgreSQL ─────────────────────────────────

export interface HistorySummary {
  id: number;
  createdAt: string;
  childAge: number | null;
  context: string;
  imageName: string;
  analysisMode: string;
  overallState: string;
  confidence: number;
  topEmotions: { name: string; intensity: number }[];
}

export interface HistoryListResponse {
  total: number;
  limit: number;
  offset: number;
  items: HistorySummary[];
}

export interface HistoryDetail {
  id: number;
  createdAt: string;
  childAge: number | null;
  context: string;
  imageName: string;
  analysisMode: string;
  overallState: string;
  confidence: number;
  result: AnalysisResult;
}

export async function fetchHistory(
  limit: number = 50,
  offset: number = 0,
): Promise<HistoryListResponse> {
  const res = await fetch(
    `${API_BASE}/history?limit=${limit}&offset=${offset}`,
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchHistoryDetail(id: number): Promise<HistoryDetail> {
  const res = await fetch(`${API_BASE}/history/${id}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteHistoryItem(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/history/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export function getHistoryImageUrl(id: number): string {
  return `${API_BASE}/history/${id}/image`;
}
