export const API_BASE = "http://localhost:8000";

export interface EmotionMeta {
  color: string;
  icon: string;
}

export const EMOTIONS: Record<string, EmotionMeta> = {
  радость: { color: "#FFD93D", icon: "☀️" },
  тревога: { color: "#FF6B6B", icon: "⚡" },
  грусть: { color: "#74B9FF", icon: "🌧️" },
  агрессия: { color: "#E17055", icon: "🔥" },
  спокойствие: { color: "#55EFC4", icon: "🌿" },
  страх: { color: "#A29BFE", icon: "🌑" },
  одиночество: { color: "#B2BEC3", icon: "🍂" },
  любовь: { color: "#FD79A8", icon: "🌸" },
  энергия: { color: "#FDCB6E", icon: "✨" },
};

export const TABS = ["Анализ", "Отчёт", "История", "О системе"] as const;
export type TabName = (typeof TABS)[number];
