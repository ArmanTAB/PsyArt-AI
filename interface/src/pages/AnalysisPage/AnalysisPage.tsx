import { useState, useEffect } from "react";
import UploadZone from "../../components/UploadZone/UploadZone";

interface Props {
  previewUrl: string | null;
  age: string;
  context: string;
  loading: boolean;
  error: string | null;
  onFile: (file: File) => void;
  onClear: () => void;
  onAgeChange: (v: string) => void;
  onContextChange: (v: string) => void;
  onAnalyze: (mode: string) => void;
}

interface OllamaStatus {
  available: boolean;
  has_llava: boolean;
  reason: string | null;
  checking: boolean;
}

export default function AnalysisPage({
  previewUrl,
  age,
  context,
  loading,
  error,
  onFile,
  onClear,
  onAgeChange,
  onContextChange,
  onAnalyze,
}: Props) {
  const [mode, setMode] = useState<"auto" | "llava" | "opencv">("auto");
  const [ollama, setOllama] = useState<OllamaStatus>({
    available: false,
    has_llava: false,
    reason: null,
    checking: true,
  });

  // Проверяем Ollama при монтировании
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch("http://localhost:8000/llava/status");
        const d = await r.json();
        setOllama({ ...d, checking: false });
      } catch {
        setOllama({
          available: false,
          has_llava: false,
          reason: "Сервер недоступен",
          checking: false,
        });
      }
    };
    check();
  }, []);

  const llavaReady = ollama.available && ollama.has_llava;

  const modeLabel: Record<string, string> = {
    auto: "Авто",
    llava: "LLaVA (ИИ)",
    opencv: "OpenCV",
  };

  const modeBg: Record<string, string> = {
    auto: "#6c5ce7",
    llava: "#00b894",
    opencv: "#0984e3",
  };

  return (
    <div
      className="fade-in"
      style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}
    >
      {/* Left — upload */}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <h2
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 28,
              color: "#2d3436",
              marginBottom: 6,
            }}
          >
            Загрузка рисунка
          </h2>
          <p style={{ color: "#636e72", fontSize: 15 }}>
            Загрузите детский рисунок для психоэмоционального анализа
          </p>
        </div>
        <UploadZone previewUrl={previewUrl} onFile={onFile} onClear={onClear} />
      </div>

      {/* Right — settings */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Режим анализа */}
        <div className="card" style={{ padding: "16px 20px" }}>
          <h4
            style={{
              fontSize: 12,
              color: "#636e72",
              letterSpacing: 0.6,
              textTransform: "uppercase",
              marginBottom: 12,
            }}
          >
            Метод анализа
          </h4>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {(["auto", "llava", "opencv"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                disabled={m === "llava" && !llavaReady}
                style={{
                  flex: 1,
                  padding: "8px 4px",
                  borderRadius: 8,
                  border: "none",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor:
                    m === "llava" && !llavaReady ? "not-allowed" : "pointer",
                  background: mode === m ? modeBg[m] : "#f0f0f0",
                  color: mode === m ? "#fff" : "#636e72",
                  opacity: m === "llava" && !llavaReady ? 0.5 : 1,
                  transition: "all .2s",
                }}
              >
                {modeLabel[m]}
              </button>
            ))}
          </div>

          {/* Статус Ollama */}
          <div
            style={{
              padding: "10px 14px",
              borderRadius: 8,
              fontSize: 13,
              background: ollama.checking
                ? "#f8f9fa"
                : llavaReady
                  ? "#eafaf1"
                  : "#fff8f0",
              border: `1px solid ${ollama.checking ? "#dee2e6" : llavaReady ? "#a9dfbf" : "#fcd89a"}`,
            }}
          >
            {ollama.checking ? (
              <span style={{ color: "#636e72" }}>⟳ Проверка Ollama...</span>
            ) : llavaReady ? (
              <span style={{ color: "#27ae60" }}>
                ✓ <b>LLaVA готова</b> — нейросеть понимает содержание рисунка
              </span>
            ) : (
              <span style={{ color: "#e67e22" }}>
                ⚠ <b>LLaVA недоступна</b> — будет использован OpenCV
                {ollama.reason && (
                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 12,
                      color: "#636e72",
                      fontFamily: "monospace",
                      background: "#fff",
                      padding: "4px 8px",
                      borderRadius: 4,
                    }}
                  >
                    {ollama.reason}
                  </div>
                )}
              </span>
            )}
          </div>

          {/* Сравнение методов */}
          <div
            style={{
              marginTop: 12,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
            }}
          >
            <div
              style={{
                background: "#eafaf1",
                borderRadius: 8,
                padding: "10px 12px",
                fontSize: 12,
              }}
            >
              <div
                style={{ fontWeight: 700, color: "#27ae60", marginBottom: 4 }}
              >
                🧠 LLaVA
              </div>
              <div style={{ color: "#555", lineHeight: 1.6 }}>
                Видит содержание
                <br />
                Понимает сюжет
                <br />
                10–20 сек
              </div>
            </div>
            <div
              style={{
                background: "#eef6ff",
                borderRadius: 8,
                padding: "10px 12px",
                fontSize: 12,
              }}
            >
              <div
                style={{ fontWeight: 700, color: "#0984e3", marginBottom: 4 }}
              >
                🔬 OpenCV
              </div>
              <div style={{ color: "#555", lineHeight: 1.6 }}>
                Цвет и линии
                <br />
                Зональный анализ
                <br />
                ~1 сек
              </div>
            </div>
          </div>
        </div>

        {/* Данные о ребёнке */}
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 18,
              marginBottom: 16,
              color: "#2d3436",
            }}
          >
            Данные о ребёнке
          </h3>
          <div style={{ marginBottom: 14 }}>
            <label>Возраст (лет)</label>
            <input
              type="number"
              placeholder="например, 7"
              value={age}
              onChange={(e) => onAgeChange(e.target.value)}
              min={2}
              max={17}
            />
          </div>
          <div>
            <label>Контекст для психолога</label>
            <textarea
              rows={3}
              placeholder="Тема рисунка, поведение ребёнка, что беспокоит..."
              value={context}
              onChange={(e) => onContextChange(e.target.value)}
              style={{ resize: "vertical" }}
            />
          </div>
        </div>

        {/* Ошибка */}
        {error && (
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
            ⚠️ {error}
            {error.includes("Failed to fetch") && (
              <div style={{ marginTop: 8, fontSize: 13, color: "#636e72" }}>
                Убедитесь что сервер запущен:{" "}
                <code>py -3.11 -m uvicorn server:app --reload</code>
              </div>
            )}
            {error.includes("503") && (
              <div style={{ marginTop: 8, fontSize: 13, color: "#636e72" }}>
                Запустите Ollama: <code>ollama serve</code>
              </div>
            )}
          </div>
        )}

        {/* Кнопка */}
        <button
          className="btn-primary"
          onClick={() => onAnalyze(mode)}
          disabled={!previewUrl || loading}
          style={{ background: loading ? "#b2bec3" : modeBg[mode] }}
        >
          {loading ? (
            <>
              <span className="spin">⟳</span>{" "}
              {mode === "llava"
                ? "LLaVA анализирует (10–20 сек)..."
                : "Анализирую..."}
            </>
          ) : (
            `▶ Запустить анализ · ${modeLabel[mode]}`
          )}
        </button>
      </div>
    </div>
  );
}
