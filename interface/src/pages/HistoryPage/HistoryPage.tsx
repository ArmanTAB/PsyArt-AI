import { HistoryEntry } from "../../types/analysis";
import { EMOTIONS } from "../../constants";
import StatusBadge from "../../components/StatusBadge/StatusBadge";

interface Props {
  history: HistoryEntry[];
  onSelect: (entry: HistoryEntry) => void;
}

export default function HistoryPage({ history, onSelect }: Props) {
  return (
    <div className="fade-in">
      <h2
        style={{
          fontFamily: "DM Serif Display, serif",
          fontSize: 28,
          color: "#2d3436",
          marginBottom: 24,
        }}
      >
        История анализов
      </h2>

      {history.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px", color: "#b2bec3" }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🗂️</div>
          <p>Нет сохранённых анализов</p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: 16,
          }}
        >
          {history.map((h) => (
            <div
              key={h.id}
              className="card history-card"
              onClick={() => onSelect(h)}
            >
              <img
                src={h.preview}
                alt=""
                style={{
                  width: "100%",
                  height: 150,
                  objectFit: "cover",
                  borderRadius: 10,
                  marginBottom: 14,
                }}
              />
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <StatusBadge status={h.result.overallState} />
                <span style={{ fontSize: 12, color: "#b2bec3" }}>{h.date}</span>
              </div>
              {h.age && (
                <p style={{ fontSize: 13, color: "#636e72" }}>
                  Возраст: {h.age} лет
                </p>
              )}
              <div
                style={{
                  marginTop: 8,
                  display: "flex",
                  gap: 6,
                  flexWrap: "wrap",
                }}
              >
                {h.result.emotions.slice(0, 2).map((e) => (
                  <span
                    key={e.name}
                    style={{
                      background: (EMOTIONS[e.name]?.color ?? "#ddd") + "22",
                      color: EMOTIONS[e.name]?.color ?? "#888",
                      padding: "2px 8px",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  >
                    {EMOTIONS[e.name]?.icon} {e.name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
