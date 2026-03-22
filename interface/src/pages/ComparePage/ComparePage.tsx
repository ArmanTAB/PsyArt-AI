import { useState, useCallback, useRef } from "react";
import { AnalysisResult } from "../../types/analysis";
import { EMOTIONS } from "../../constants";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import UploadZone from "../../components/UploadZone/UploadZone";

const API_BASE = "http://localhost:8000";

interface ModeResult {
  mode: string;
  label: string;
  color: string;
  result: AnalysisResult | null;
  loading: boolean;
  error: string | null;
  time: number | null;
}

const MODES: { mode: string; label: string; color: string }[] = [
  { mode: "opencv", label: "OpenCV", color: "#0984e3" },
  { mode: "groq", label: "Groq LLM", color: "#00b894" },
  { mode: "hybrid", label: "Гибрид", color: "#6c5ce7" },
];

export default function ComparePage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreview] = useState<string | null>(null);
  const [age, setAge] = useState("");
  const [context, setContext] = useState("");
  const [results, setResults] = useState<ModeResult[]>(
    MODES.map((m) => ({
      ...m,
      result: null,
      loading: false,
      error: null,
      time: null,
    })),
  );
  const [running, setRunning] = useState(false);
  const abortRef = useRef(false);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResults(
      MODES.map((m) => ({
        ...m,
        result: null,
        loading: false,
        error: null,
        time: null,
      })),
    );
  }, []);

  const handleClear = useCallback(() => {
    setFile(null);
    setPreview(null);
    setResults(
      MODES.map((m) => ({
        ...m,
        result: null,
        loading: false,
        error: null,
        time: null,
      })),
    );
  }, []);

  const runComparison = async () => {
    if (!file) return;
    setRunning(true);
    abortRef.current = false;

    // Запускаем все 3 режима параллельно
    const promises = MODES.map(async (m, idx) => {
      setResults((prev) => {
        const copy = [...prev];
        copy[idx] = {
          ...copy[idx],
          loading: true,
          error: null,
          result: null,
          time: null,
        };
        return copy;
      });

      const start = performance.now();
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("mode", m.mode);
        form.append("save", "false");
        if (age) form.append("age", age);
        if (context) form.append("context", context);

        const res = await fetch(`${API_BASE}/analyze`, {
          method: "POST",
          body: form,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const elapsed = Math.round(performance.now() - start);

        setResults((prev) => {
          const copy = [...prev];
          copy[idx] = {
            ...copy[idx],
            result: data,
            loading: false,
            time: elapsed,
          };
          return copy;
        });
      } catch (e) {
        const elapsed = Math.round(performance.now() - start);
        setResults((prev) => {
          const copy = [...prev];
          copy[idx] = {
            ...copy[idx],
            error: (e as Error).message,
            loading: false,
            time: elapsed,
          };
          return copy;
        });
      }
    });

    await Promise.allSettled(promises);
    setRunning(false);
  };

  const hasResults = results.some((r) => r.result !== null);

  return (
    <div className="fade-in">
      <h2
        style={{
          fontFamily: "DM Serif Display, serif",
          fontSize: 28,
          color: "#2d3436",
          marginBottom: 6,
        }}
      >
        Сравнение режимов
      </h2>
      <p style={{ color: "#636e72", fontSize: 15, marginBottom: 20 }}>
        Один рисунок — три режима анализа. Показывает разницу между OpenCV, Groq
        и гибридным подходом.
      </p>

      {/* Загрузка + параметры */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
          marginBottom: 24,
        }}
      >
        <UploadZone
          previewUrl={previewUrl}
          onFile={handleFile}
          onClear={handleClear}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="card">
            <div style={{ marginBottom: 12 }}>
              <label>
                Возраст (лет) <span style={{ color: "#e17055" }}>*</span>
              </label>
              <input
                type="number"
                placeholder="Введите возраст ребёнка"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                min={2}
                max={17}
                style={{ borderColor: !age ? "#fcd89a" : undefined }}
              />
            </div>
            <div>
              <label>Контекст</label>
              <textarea
                rows={2}
                placeholder="Опционально..."
                value={context}
                onChange={(e) => setContext(e.target.value)}
                style={{ resize: "vertical" }}
              />
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={runComparison}
            disabled={!file || !age || running}
            style={{
              background: running || !file || !age ? "#b2bec3" : "#6c5ce7",
            }}
          >
            {running ? "Анализ идёт..." : "Запустить сравнение (3 режима)"}
          </button>
        </div>
      </div>

      {/* Результаты в 3 колонках */}
      {(running || hasResults) && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 16,
          }}
        >
          {results.map((r) => (
            <div
              key={r.mode}
              className="card"
              style={{
                borderTop: `3px solid ${r.color}`,
                opacity: r.loading ? 0.6 : 1,
                transition: "opacity 0.3s",
              }}
            >
              {/* Заголовок режима */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 12,
                }}
              >
                <span style={{ fontWeight: 700, fontSize: 15, color: r.color }}>
                  {r.label}
                </span>
                {r.time !== null && (
                  <span
                    style={{
                      fontSize: 11,
                      color: "#b2bec3",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {r.time}мс
                  </span>
                )}
              </div>

              {/* Загрузка */}
              {r.loading && (
                <div
                  style={{
                    textAlign: "center",
                    padding: "40px 0",
                    color: "#b2bec3",
                  }}
                >
                  <span className="spin" style={{ fontSize: 20 }}>
                    &#8635;
                  </span>
                  <p style={{ marginTop: 8, fontSize: 13 }}>Анализ...</p>
                </div>
              )}

              {/* Ошибка */}
              {r.error && (
                <div
                  style={{
                    padding: "12px",
                    background: "#fff5f5",
                    borderRadius: 8,
                    fontSize: 13,
                    color: "#c0392b",
                  }}
                >
                  {r.error}
                </div>
              )}

              {/* Результат */}
              {r.result && (
                <div>
                  {/* Статус */}
                  <div style={{ marginBottom: 12 }}>
                    <StatusBadge status={r.result.overallState} />
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 12,
                        color: "#636e72",
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      {r.result.confidence}%
                    </span>
                  </div>

                  {/* Эмоции */}
                  <div style={{ marginBottom: 14 }}>
                    {r.result.emotions.map((e) => {
                      const em = EMOTIONS[e.name] ?? {
                        color: "#ccc",
                        label: e.name,
                      };
                      return (
                        <div key={e.name} style={{ marginBottom: 8 }}>
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              fontSize: 13,
                              marginBottom: 3,
                            }}
                          >
                            <span
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                              }}
                            >
                              <span
                                style={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  background: em.color,
                                  display: "inline-block",
                                }}
                              />
                              {em.label}
                            </span>
                            <span
                              style={{
                                fontFamily: "JetBrains Mono, monospace",
                                fontSize: 12,
                                fontWeight: 700,
                                color: em.color,
                              }}
                            >
                              {e.intensity}%
                            </span>
                          </div>
                          <div
                            style={{
                              height: 6,
                              background: "#f0f0f0",
                              borderRadius: 6,
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                height: "100%",
                                width: `${e.intensity}%`,
                                background: em.color,
                                borderRadius: 6,
                                transition: "width 0.8s ease",
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Объекты */}
                  {r.result.contentAnalysis &&
                    r.result.contentAnalysis.detectedObjects.length > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <div
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: "#636e72",
                            textTransform: "uppercase",
                            marginBottom: 6,
                          }}
                        >
                          Обнаружено
                        </div>
                        <div
                          style={{ display: "flex", flexWrap: "wrap", gap: 4 }}
                        >
                          {r.result.contentAnalysis.detectedObjects
                            .slice(0, 6)
                            .map((obj) => (
                              <span
                                key={obj}
                                style={{
                                  fontSize: 11,
                                  padding: "2px 8px",
                                  borderRadius: 10,
                                  background: "#f5f3ff",
                                  color: "#6c5ce7",
                                  border: "1px solid #e2d9f3",
                                }}
                              >
                                {obj}
                              </span>
                            ))}
                        </div>
                      </div>
                    )}

                  {/* Портрет (сокращённый) */}
                  <p
                    style={{
                      fontSize: 12,
                      color: "#636e72",
                      lineHeight: 1.5,
                      borderTop: "1px solid #f0ece8",
                      paddingTop: 10,
                    }}
                  >
                    {r.result.psychologicalPortrait.slice(0, 200)}
                    {r.result.psychologicalPortrait.length > 200 ? "..." : ""}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
