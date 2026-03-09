import { AnalysisResult } from "../../types/analysis";
import EmotionBar from "../../components/EmotionBar/EmotionBar";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import ColorSwatch from "../../components/ColorSwatch/ColorSwatch";

interface Props {
  result: AnalysisResult | null;
  age: string;
  onBack: () => void;
}

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

  return (
    <div
      className="fade-in"
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {/* Header card */}
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
            {/* Бейдж режима */}
            {result.analysisMode && (
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: 20,
                  background:
                    result.analysisMode === "llava"
                      ? "#00b894"
                      : result.analysisMode === "opencv_fallback"
                        ? "#e17055"
                        : "#0984e3",
                  color: "#fff",
                  letterSpacing: 0.5,
                }}
              >
                {result.analysisMode === "llava"
                  ? "🧠 LLaVA"
                  : result.analysisMode === "opencv_fallback"
                    ? "⚠ OpenCV (fallback)"
                    : "🔬 OpenCV"}
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
          {result.fallbackReason && (
            <p style={{ color: "#fdcb6e", fontSize: 12, marginTop: 4 }}>
              ⚠ {result.fallbackReason}
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

      {/* LLaVA: блок распознанного содержимого */}
      {result.contentAnalysis &&
        result.contentAnalysis.detectedObjects?.length > 0 && (
          <div
            className="card"
            style={{ background: "#eafaf1", borderColor: "#a9dfbf" }}
          >
            <h4
              style={{
                fontSize: 13,
                color: "#27ae60",
                letterSpacing: 0.5,
                textTransform: "uppercase",
                marginBottom: 10,
              }}
            >
              🧠 LLaVA: содержимое рисунка
            </h4>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginBottom: 10,
              }}
            >
              {result.contentAnalysis.detectedObjects.map((obj, i) => (
                <span
                  key={i}
                  style={{
                    background: "#fff",
                    border: "1px solid #a9dfbf",
                    borderRadius: 20,
                    padding: "3px 10px",
                    fontSize: 13,
                    color: "#2d3436",
                  }}
                >
                  {obj}
                </span>
              ))}
            </div>
            <div
              style={{
                display: "flex",
                gap: 16,
                fontSize: 13,
                color: "#555",
                flexWrap: "wrap",
              }}
            >
              {result.contentAnalysis.hasHuman && <span>👤 Люди</span>}
              {result.contentAnalysis.hasSun && <span>☀️ Солнце</span>}
              {result.contentAnalysis.hasHouse && <span>🏠 Дом</span>}
              {result.contentAnalysis.hasNature && <span>🌿 Природа</span>}
              {result.contentAnalysis.hasSmile && <span>😊 Улыбка</span>}
              {result.contentAnalysis.hasDarkElements && (
                <span>🌑 Тёмные элементы</span>
              )}
            </div>
            {result.contentAnalysis.symbolism && (
              <p
                style={{
                  marginTop: 10,
                  fontSize: 13,
                  color: "#2d6a4f",
                  fontStyle: "italic",
                }}
              >
                {result.contentAnalysis.symbolism}
              </p>
            )}
          </div>
        )}

      {/* Emotions + Color/Composition grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 20,
              marginBottom: 20,
              color: "#2d3436",
            }}
          >
            Эмоциональный профиль
          </h3>
          {result.emotions.length > 0 ? (
            result.emotions.map((e) => <EmotionBar key={e.name} {...e} />)
          ) : (
            <p style={{ color: "#b2bec3" }}>Эмоции не определены</p>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Color */}
          <div className="card">
            <h3
              style={{
                fontFamily: "DM Serif Display, serif",
                fontSize: 18,
                marginBottom: 14,
                color: "#2d3436",
              }}
            >
              🎨 Цветовой анализ
            </h3>
            <div
              style={{
                display: "flex",
                gap: 8,
                marginBottom: 12,
                alignItems: "center",
              }}
            >
              {result.colorAnalysis.dominant.map((hex) => (
                <ColorSwatch key={hex} hex={hex} />
              ))}
              <span
                style={{
                  background: "#e8f5e9",
                  color: "#2e7d32",
                  padding: "3px 10px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontWeight: 600,
                  marginLeft: 4,
                }}
              >
                {result.colorAnalysis.palette}
              </span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 8,
                marginBottom: 12,
              }}
            >
              {(
                [
                  [
                    "Яркость",
                    result.colorAnalysis.brightnessValue + "%",
                    result.colorAnalysis.brightnessClass,
                  ],
                  [
                    "Насыщенность",
                    result.colorAnalysis.saturationValue + "%",
                    result.colorAnalysis.saturationClass,
                  ],
                ] as [string, string, string][]
              ).map(([label, val, cls]) => (
                <div
                  key={label}
                  style={{
                    background: "#f8f8f8",
                    borderRadius: 10,
                    padding: "10px 14px",
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      color: "#b2bec3",
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 18,
                      fontWeight: 700,
                      color: "#2d3436",
                    }}
                  >
                    {val}
                  </div>
                  <div style={{ fontSize: 12, color: "#636e72" }}>{cls}</div>
                </div>
              ))}
            </div>
            <p style={{ fontSize: 13, color: "#636e72", lineHeight: 1.7 }}>
              {result.colorAnalysis.interpretation}
            </p>
          </div>

          {/* Composition */}
          <div className="card">
            <h3
              style={{
                fontFamily: "DM Serif Display, serif",
                fontSize: 18,
                marginBottom: 14,
                color: "#2d3436",
              }}
            >
              📐 Композиция
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: 8,
                marginBottom: 12,
              }}
            >
              {(
                [
                  ["Заполнение", result.composition.fillRatio + "%"],
                  ["Объектов", String(result.composition.numObjects)],
                  ["Расположение", result.composition.location],
                ] as [string, string][]
              ).map(([label, val]) => (
                <div
                  key={label}
                  style={{
                    background: "#f8f8f8",
                    borderRadius: 10,
                    padding: "10px 14px",
                    textAlign: "center",
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      color: "#b2bec3",
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 16,
                      fontWeight: 700,
                      color: "#2d3436",
                      marginTop: 4,
                    }}
                  >
                    {val}
                  </div>
                </div>
              ))}
            </div>
            <p style={{ fontSize: 13, color: "#636e72", lineHeight: 1.7 }}>
              {result.composition.interpretation}
            </p>
          </div>
        </div>
      </div>

      {/* Psychological portrait */}
      <div
        className="card"
        style={{
          background: "#fffbf0",
          borderColor: "#ffe082",
          borderLeft: "4px solid #FFD93D",
        }}
      >
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 20,
            marginBottom: 12,
            color: "#2d3436",
          }}
        >
          Психологический портрет
        </h3>
        <p style={{ fontSize: 16, color: "#4a4a4a", lineHeight: 1.8 }}>
          {result.psychologicalPortrait}
        </p>
      </div>

      {/* Risks + Recommendations */}
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

      {/* Color ratios chart */}
      {Object.keys(result.colorAnalysis.colorRatios).length > 0 && (
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 18,
              marginBottom: 16,
              color: "#2d3436",
            }}
          >
            📊 Распределение цветовых групп
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {Object.entries(result.colorAnalysis.colorRatios)
              .sort(([, a], [, b]) => b - a)
              .map(([name, pct]) => (
                <div
                  key={name}
                  style={{
                    background: "#f5f5f5",
                    borderRadius: 10,
                    padding: "8px 14px",
                    minWidth: 100,
                  }}
                >
                  <div
                    style={{ fontSize: 12, color: "#636e72", marginBottom: 4 }}
                  >
                    {name}
                  </div>
                  <div
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 16,
                      fontWeight: 700,
                      color: "#2d3436",
                    }}
                  >
                    {pct}%
                  </div>
                  <div
                    style={{
                      height: 4,
                      background: "#e0e0e0",
                      borderRadius: 4,
                      marginTop: 6,
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(pct * 3, 100)}%`,
                        background: "#6c5ce7",
                        borderRadius: 4,
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
