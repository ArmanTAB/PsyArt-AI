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
  onAnalyze: () => void;
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
  return (
    <div
      className="fade-in"
      style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}
    >
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
            Загрузите детский рисунок для психоэмоционального анализа на основе
            компьютерного зрения
          </p>
        </div>
        <UploadZone previewUrl={previewUrl} onFile={onFile} onClear={onClear} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="card">
          <h3
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 20,
              marginBottom: 20,
              color: "#2d3436",
            }}
          >
            Данные о ребёнке
          </h3>
          <div style={{ marginBottom: 16 }}>
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
              rows={4}
              placeholder="Тема рисунка, поведение, что беспокоит родителей..."
              value={context}
              onChange={(e) => onContextChange(e.target.value)}
              style={{ resize: "vertical" }}
            />
          </div>
        </div>

        <div
          className="card"
          style={{ background: "#f8f5ff", borderColor: "#e2d9f3" }}
        >
          <h4
            style={{
              fontSize: 13,
              color: "#6c5ce7",
              marginBottom: 10,
              letterSpacing: 0.5,
              textTransform: "uppercase",
            }}
          >
            🔬 Технология анализа
          </h4>
          <div style={{ fontSize: 13, color: "#636e72", lineHeight: 1.7 }}>
            <b>OpenCV:</b> K-Means кластеризация цветов, анализ моментов,
            контуры
            <br />
            <b>scikit-learn:</b> KMeans для доминирующей палитры
            <br />
            <b>Психология:</b> Тест Люшера, правила арт-терапии
            <br />
            <b>Нет внешних API</b> — всё работает локально
          </div>
        </div>

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
                <code>uvicorn server:app --reload</code>
              </div>
            )}
          </div>
        )}

        <button
          className="btn-primary"
          onClick={onAnalyze}
          disabled={!previewUrl || loading}
        >
          {loading ? (
            <>
              <span className="spin">⟳</span> Анализирую...
            </>
          ) : (
            "▶ Запустить анализ"
          )}
        </button>
      </div>
    </div>
  );
}
