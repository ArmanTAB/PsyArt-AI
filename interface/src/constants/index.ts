export const API_BASE = "http://localhost:8000";

export interface EmotionMeta {
  color: string;
  label: string;
}

export const EMOTIONS: Record<string, EmotionMeta> = {
  радость: { color: "#FFD93D", label: "Радость" },
  тревога: { color: "#FF6B6B", label: "Тревога" },
  грусть: { color: "#74B9FF", label: "Грусть" },
  агрессия: { color: "#E17055", label: "Агрессия" },
  спокойствие: { color: "#55EFC4", label: "Спокойствие" },
};

export const TABS = [
  "Анализ",
  "Отчёт",
  "Сравнение",
  "История",
  "О системе",
] as const;
export type TabName = (typeof TABS)[number];
