import { useState, useEffect, useCallback } from "react";
import { AnalysisResult, OverallState } from "../../types/analysis";
import { EMOTIONS } from "../../constants";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import {
  fetchHistory,
  fetchHistoryDetail,
  deleteHistoryItem,
  getHistoryImageUrl,
  HistorySummary,
} from "../../api/analyzeService";

interface Props {
  onSelect: (result: AnalysisResult, age: string) => void;
}

export default function HistoryPage({ onSelect }: Props) {
  const [items, setItems] = useState<HistorySummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHistory(50, 0);
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleSelect = async (id: number) => {
    try {
      const detail = await fetchHistoryDetail(id);
      onSelect(detail.result, detail.childAge?.toString() ?? "");
    } catch (e) {
      setError(`Ошибка загрузки: ${(e as Error).message}`);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm("Удалить этот анализ?")) return;
    setDeletingId(id);
    try {
      await deleteHistoryItem(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      setTotal((prev) => prev - 1);
    } catch (err) {
      setError(`Ошибка удаления: ${(err as Error).message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="fade-in">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <h2
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 28,
            color: "#2d3436",
          }}
        >
          История анализов
        </h2>
        {total > 0 && (
          <span style={{ fontSize: 13, color: "#b2bec3" }}>Всего: {total}</span>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "60px", color: "#b2bec3" }}>
          <p>Загрузка...</p>
        </div>
      ) : error ? (
        <div
          style={{
            background: "#fff5f5",
            border: "1px solid #ffd6d6",
            borderRadius: 12,
            padding: 16,
            color: "#c0392b",
            fontSize: 14,
          }}
        >
          {error}
        </div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px", color: "#b2bec3" }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: "#f0ecff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px",
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6c5ce7"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <p>Нет сохранённых анализов</p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 16,
          }}
        >
          {items.map((h) => (
            <div
              key={h.id}
              className="card history-card"
              onClick={() => handleSelect(h.id)}
              style={{ position: "relative" }}
            >
              {/* Изображение из БД */}
              <img
                src={getHistoryImageUrl(h.id)}
                alt={h.imageName}
                style={{
                  width: "100%",
                  height: 150,
                  objectFit: "cover",
                  borderRadius: 10,
                  marginBottom: 14,
                  background: "#f5f5f5",
                }}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />

              {/* Кнопка удаления */}
              <button
                onClick={(e) => handleDelete(e, h.id)}
                disabled={deletingId === h.id}
                style={{
                  position: "absolute",
                  top: 8,
                  right: 8,
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: "rgba(255,255,255,0.9)",
                  border: "1px solid #e0dbd5",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  color: "#636e72",
                  opacity: deletingId === h.id ? 0.5 : 1,
                }}
                title="Удалить"
              >
                &#x2715;
              </button>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <StatusBadge status={h.overallState as OverallState} />
                <span style={{ fontSize: 11, color: "#b2bec3" }}>
                  {formatDate(h.createdAt)}
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 6,
                }}
              >
                {h.childAge && (
                  <span style={{ fontSize: 13, color: "#636e72" }}>
                    Возраст: {h.childAge} лет
                  </span>
                )}
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 10,
                    background: "#f0f0ff",
                    color: "#6c5ce7",
                    fontWeight: 600,
                  }}
                >
                  {h.analysisMode}
                </span>
              </div>

              {h.topEmotions.length > 0 && (
                <div
                  style={{
                    marginTop: 8,
                    display: "flex",
                    gap: 6,
                    flexWrap: "wrap",
                  }}
                >
                  {h.topEmotions.map((e) => (
                    <span
                      key={e.name}
                      style={{
                        background: (EMOTIONS[e.name]?.color ?? "#ddd") + "22",
                        color: EMOTIONS[e.name]?.color ?? "#888",
                        padding: "2px 8px",
                        borderRadius: 12,
                        fontSize: 12,
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          background: EMOTIONS[e.name]?.color ?? "#888",
                          display: "inline-block",
                        }}
                      />
                      {e.name} {e.intensity}%
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
