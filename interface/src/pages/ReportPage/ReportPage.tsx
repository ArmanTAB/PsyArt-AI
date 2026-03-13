import { AnalysisResult } from "../../types/analysis";
import EmotionBar from "../../components/EmotionBar/EmotionBar";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import ColorSwatch from "../../components/ColorSwatch/ColorSwatch";

interface Props {
  result: AnalysisResult | null;
  age: string;
  onBack: () => void;
}

const MODE_BADGE: Record<string, { bg: string; label: string }> = {
  claude: { bg: "#6c5ce7", label: "🧠 Claude" },
  claude_hybrid: { bg: "#a29bfe", label: "🧠+🔬 Claude+OpenCV" },
  groq: { bg: "#00b894", label: "🧠 Groq" },
  hybrid: { bg: "#fd79a8", label: "🔀 Гибрид" },
  opencv: { bg: "#0984e3", label: "🔬 OpenCV" },
  opencv_fallback: { bg: "#e17055", label: "⚠ OpenCV (fallback)" },
};

export default function ReportPage({ result, age, onBack }: Props) {
  if (!result) {
    return (
      <div
        className="fade-in"
        style={{ textAlign: "center", padding: "80px 40px", color: "#b2bec3" }}
      >
        <div style={{ fontSize: 64, marginBottom: 16 }}>📊</div>
        <p style={{ fontSize: 18 }}>Загрузите рисунок и запустите анализ</p>
        <button
          className="btn-primary"
          style={{ marginTop: 20, width: "auto", padding: "12px 28px" }}
          onClick={onBack}
        >
          ← К анализу
        </button>
      </div>
    );
  }

  const modeBadge = result.analysisMode
    ? (MODE_BADGE[result.analysisMode] ?? MODE_BADGE["opencv"])
    : null;

  return (
    <div
      className="fade-in"
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {/* Header */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg,#2d3436,#1a1a2e)",
          border: "none",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 4,
            }}
          >
            <div style={{ color: "#a29bfe", fontSize: 12, letterSpacing: 1 }}>
              ПСИХОЛОГИЧЕСКИЙ ОТЧЁТ
            </div>
            {modeBadge && (
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: 20,
                  background: modeBadge.bg,
                  color: "#fff",
                  letterSpacing: 0.5,
                }}
              >
                {modeBadge.label}
              </span>
            )}
          </div>

          <h2
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 26,
              color: "#fff",
            }}
          >
            Результаты анализа
          </h2>

          {age && (
            <p style={{ color: "#b2bec3", fontSize: 14, marginTop: 4 }}>
              Возраст: {age} лет
            </p>
          )}

          {result.ageNormLabel && (
            <p style={{ color: "#a29bfe", fontSize: 12, marginTop: 4 }}>
              📐 {result.ageNormLabel}
            </p>
          )}

          {result.fallbackReason && (
            <p style={{ color: "#fdcb6e", fontSize: 12, marginTop: 4 }}>
              ⚠ {result.fallbackReason}
            </p>
          )}

          {result.contextAnalysis &&
            result.contextAnalysis.stress_level > 0 && (
              <p style={{ color: "#e17055", fontSize: 12, marginTop: 4 }}>
                🔴 Стресс-контекст учтён (
                {result.contextAnalysis.stress_keywords.join(", ")})
              </p>
            )}
        </div>

        <div style={{ textAlign: "right" }}>
          <StatusBadge status={result.overallState} />
          <div style={{ color: "#636e72", fontSize: 13, marginTop: 8 }}>
            Уверенность:{" "}
            <span
              style={{
                color: "#a29bfe",
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: 700,
              }}
            >
              {result.confidence}%
            </span>
          </div>
        </div>
      </div>

      {/* Содержание рисунка */}
      {result.contentAnalysis &&
        result.contentAnalysis.detectedObjects?.length > 0 && (
          <div className="card">
            <h3
              style={{
                fontFamily: "DM Serif Display, serif",
                fontSize: 18,
                marginBottom: 12,
                color: "#2d3436",
              }}
            >
              🎨 Содержание рисунка
            </h3>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginBottom: 12,
              }}
            >
              {result.contentAnalysis.detectedObjects.map((obj) => (
                <span
                  key={obj}
                  style={{
                    background: "#f0f0ff",
                    border: "1px solid #a29bfe",
                    borderRadius: 20,
                    padding: "4px 12px",
                    fontSize: 13,
                    color: "#6c5ce7",
                    fontWeight: 600,
                  }}
                >
                  {obj}
                </span>
              ))}
            </div>
            {result.contentAnalysis.symbolism && (
              <p style={{ fontSize: 14, color: "#636e72", lineHeight: 1.6 }}>
                {result.contentAnalysis.symbolism}
              </p>
            )}
          </div>
        )}

      {/* Эмоциональный профиль */}
      <div className="card">
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 18,
            marginBottom: 16,
            color: "#2d3436",
          }}
        >
          Эмоциональный профиль
        </h3>
        {result.emotions.map((e) => (
          <EmotionBar key={e.name} {...e} />
        ))}
      </div>

      {/* Психологический портрет */}
      <div className="card">
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 18,
            marginBottom: 12,
            color: "#2d3436",
          }}
        >
          Психологический портрет
        </h3>
        <p style={{ fontSize: 15, color: "#4a4a4a", lineHeight: 1.8 }}>
          {result.psychologicalPortrait}
        </p>
      </div>

      {/* Риски + Рекомендации */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {result.riskFactors.length > 0 && (
          <div className="card">
            <h3
              style={{
                fontFamily: "DM Serif Display, serif",
                fontSize: 18,
                marginBottom: 14,
                color: "#2d3436",
              }}
            >
              ⚠️ Факторы риска
            </h3>
            {result.riskFactors.map((r) => (
              <span key={r} className="risk-tag">
                {r}
              </span>
            ))}
          </div>
        )}
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 18,
              marginBottom: 14,
              color: "#2d3436",
            }}
          >
            💡 Рекомендации
          </h3>
          {result.recommendations.map((r, i) => (
            <div key={i} className="recommendation-item">
              <span
                style={{
                  minWidth: 24,
                  height: 24,
                  background: "#6c5ce7",
                  color: "#fff",
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono, monospace",
                }}
              >
                {i + 1}
              </span>
              <span style={{ fontSize: 14, color: "#4a4a4a", lineHeight: 1.6 }}>
                {r}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Цветовой анализ */}
      {Object.keys(result.colorAnalysis.colorRatios).length > 0 && (
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 18,
              marginBottom: 14,
              color: "#2d3436",
            }}
          >
            🎨 Цветовой анализ (Люшер)
          </h3>
          <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
            {result.colorAnalysis.dominant.map((hex) => (
              <ColorSwatch key={hex} hex={hex} />
            ))}
          </div>
          <p style={{ fontSize: 14, color: "#636e72", marginBottom: 10 }}>
            {result.colorAnalysis.interpretation}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {Object.entries(result.colorAnalysis.colorRatios)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 6)
              .map(([name, ratio]) => (
                <span
                  key={name}
                  style={{
                    fontSize: 12,
                    padding: "3px 10px",
                    borderRadius: 12,
                    background: "#f5f5f5",
                    color: "#4a4a4a",
                  }}
                >
                  {name} {ratio}%
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Зональный анализ */}
      {result.zoneAnalysis && (
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 18,
              marginBottom: 12,
              color: "#2d3436",
            }}
          >
            📐 Зональный анализ (Маховер)
          </h3>
          <p style={{ fontSize: 14, color: "#636e72", marginBottom: 12 }}>
            {result.zoneAnalysis.balanceInterpretation}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {Object.entries(result.zoneAnalysis.zoneClasses).map(
              ([zone, cls]) => (
                <span
                  key={zone}
                  style={{
                    fontSize: 12,
                    padding: "4px 12px",
                    borderRadius: 12,
                    background:
                      cls === "высокая"
                        ? "#eafaf1"
                        : cls === "низкая"
                          ? "#fff5f5"
                          : "#f5f5f5",
                    color:
                      cls === "высокая"
                        ? "#27ae60"
                        : cls === "низкая"
                          ? "#e17055"
                          : "#636e72",
                    fontWeight: 600,
                  }}
                >
                  {zone}: {cls}
                </span>
              ),
            )}
          </div>
        </div>
      )}

      {/* Кнопка назад */}
      <button
        className="btn-primary"
        style={{ background: "#636e72", marginTop: 8 }}
        onClick={onBack}
      >
        ← Новый анализ
      </button>
    </div>
  );
}
