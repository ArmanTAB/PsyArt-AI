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

interface ApiStatus {
  available: boolean;
  model?: string;
  error?: string;
  checking: boolean;
  test_accuracy?: number;
}

type Tab = "cnn" | "opencv" | "groq";

const TAB_META: Record<
  Tab,
  { label: string; color: string; desc: string; speed: string }
> = {
  cnn: {
    label: "CNN",
    color: "#e84393",
    desc: "EfficientNet-B0, дообученный на 1100+ детских рисунках. Работает локально на GPU.",
    speed: "~50 мс",
  },
  opencv: {
    label: "OpenCV",
    color: "#0984e3",
    desc: "Анализ пикселей: цвет, линии, зоны, нажим, текстура. Работает без интернета.",
    speed: "~200 мс",
  },
  groq: {
    label: "Groq LLM",
    color: "#00b894",
    desc: "LLaMA-4 Vision — понимает содержание и сюжет рисунка. Бесплатный API.",
    speed: "2-5 сек",
  },
};

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
  const [tab, setTab] = useState<Tab>("cnn");
  const [hybrid, setHybrid] = useState(true);

  const [groqStatus, setGroqStatus] = useState<ApiStatus>({
    available: false,
    checking: true,
  });
  const [cnnStatus, setCnnStatus] = useState<ApiStatus>({
    available: false,
    checking: true,
  });

  useEffect(() => {
    const checkAll = async () => {
      try {
        const gr = await fetch("http://localhost:8000/groq/status").then((r) =>
          r.json(),
        );
        setGroqStatus({ ...gr, checking: false });
      } catch {
        setGroqStatus({
          available: false,
          error: "Сервер недоступен",
          checking: false,
        });
      }
      try {
        const cn = await fetch("http://localhost:8000/cnn/status").then((r) =>
          r.json(),
        );
        setCnnStatus({ ...cn, checking: false });
      } catch {
        setCnnStatus({
          available: false,
          error: "Сервер недоступен",
          checking: false,
        });
      }
    };
    checkAll();
  }, []);

  const isAvailable = (t: Tab) => {
    if (t === "opencv") return true;
    if (t === "groq") return groqStatus.available;
    if (t === "cnn") return cnnStatus.available;
    return false;
  };

  const getMode = (): string => {
    if (tab === "cnn") return "cnn";
    if (tab === "opencv") return "opencv";
    if (tab === "groq") return hybrid ? "hybrid" : "groq";
    return "cnn";
  };

  const activeColor = TAB_META[tab].color;

  const statusOf = (t: Tab): ApiStatus => {
    if (t === "groq") return groqStatus;
    if (t === "cnn") return cnnStatus;
    return { available: true, checking: false };
  };

  const loadingMsg = () => {
    if (tab === "cnn") return "CNN анализирует...";
    if (tab === "groq")
      return hybrid ? "Groq + OpenCV анализируют..." : "Groq анализирует...";
    return "OpenCV анализирует...";
  };

  const confidenceLabel = () => {
    if (tab === "cnn")
      return cnnStatus.test_accuracy
        ? `${Math.round(cnnStatus.test_accuracy * 100)}%`
        : "75%";
    if (tab === "groq") return "64%";
    return "31%";
  };

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
            Загрузите детский рисунок для психоэмоционального анализа
          </p>
        </div>
        <UploadZone previewUrl={previewUrl} onFile={onFile} onClear={onClear} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ display: "flex", borderBottom: "1px solid #f0f0f0" }}>
            {(Object.keys(TAB_META) as Tab[]).map((t) => {
              const meta = TAB_META[t];
              const active = tab === t;
              const avail = isAvailable(t);
              const checking = statusOf(t).checking;
              return (
                <button
                  key={t}
                  onClick={() => avail && setTab(t)}
                  style={{
                    flex: 1,
                    padding: "14px 8px",
                    border: "none",
                    borderBottom: active
                      ? `3px solid ${meta.color}`
                      : "3px solid transparent",
                    background: active ? "#fafafa" : "white",
                    cursor: avail ? "pointer" : "not-allowed",
                    opacity: !avail && !checking ? 0.5 : 1,
                    transition: "all .2s",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: active ? meta.color : "#636e72",
                    }}
                  >
                    {meta.label}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: checking
                        ? "#b2bec3"
                        : avail
                          ? "#27ae60"
                          : "#e17055",
                    }}
                  >
                    {checking ? "..." : avail ? "Готов" : "Недоступен"}
                  </span>
                </button>
              );
            })}
          </div>

          <div style={{ padding: "16px 20px" }}>
            <p
              style={{
                fontSize: 13,
                color: "#4a4a4a",
                marginBottom: 14,
                lineHeight: 1.6,
              }}
            >
              {TAB_META[tab].desc}
            </p>

            {tab === "groq" && (
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 14px",
                  borderRadius: 8,
                  background: hybrid ? "#f0fff8" : "#f8f9fa",
                  border: `1px solid ${hybrid ? "#00b894" : "#dee2e6"}`,
                  cursor: "pointer",
                  marginBottom: 12,
                }}
              >
                <input
                  type="checkbox"
                  checked={hybrid}
                  onChange={(e) => setHybrid(e.target.checked)}
                  style={{ accentColor: activeColor, width: 16, height: 16 }}
                />
                <div>
                  <div
                    style={{ fontSize: 13, fontWeight: 600, color: "#2d3436" }}
                  >
                    Гибридный режим (+OpenCV)
                  </div>
                  <div style={{ fontSize: 11, color: "#636e72" }}>
                    Groq 65% + OpenCV 35%
                  </div>
                </div>
              </label>
            )}

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: 8,
              }}
            >
              {[
                { label: "Скорость", value: TAB_META[tab].speed },
                { label: "Точность", value: confidenceLabel() },
                {
                  label: "Метод",
                  value:
                    tab === "cnn"
                      ? "EfficientNet"
                      : tab === "opencv"
                        ? "Пиксели"
                        : "LLaMA-4",
                },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  style={{
                    background: "#f8f9fa",
                    borderRadius: 8,
                    padding: "8px 10px",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: 11, color: "#636e72" }}>{label}</div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: activeColor,
                    }}
                  >
                    {value}
                  </div>
                </div>
              ))}
            </div>

            {tab === "cnn" && !cnnStatus.checking && !cnnStatus.available && (
              <div
                style={{
                  marginTop: 12,
                  padding: "10px 14px",
                  borderRadius: 8,
                  background: "#fff8f0",
                  border: "1px solid #fcd89a",
                  fontSize: 12,
                  color: "#e67e22",
                }}
              >
                CNN модель не найдена. Запустите{" "}
                <code
                  style={{
                    background: "#fff",
                    padding: "1px 4px",
                    borderRadius: 3,
                  }}
                >
                  py -3.11 train_cnn.py
                </code>
              </div>
            )}

            {tab === "groq" &&
              !groqStatus.checking &&
              !groqStatus.available && (
                <div
                  style={{
                    marginTop: 12,
                    padding: "10px 14px",
                    borderRadius: 8,
                    background: "#fff8f0",
                    border: "1px solid #fcd89a",
                    fontSize: 12,
                    color: "#e67e22",
                  }}
                >
                  Groq недоступен — добавьте{" "}
                  <code
                    style={{
                      background: "#fff",
                      padding: "1px 4px",
                      borderRadius: 3,
                    }}
                  >
                    GROQ_API_KEY
                  </code>{" "}
                  в{" "}
                  <code
                    style={{
                      background: "#fff",
                      padding: "1px 4px",
                      borderRadius: 3,
                    }}
                  >
                    core/.env
                  </code>
                </div>
              )}
          </div>
        </div>

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
            <label>
              Возраст (лет) <span style={{ color: "#e17055" }}>*</span>
            </label>
            <input
              type="number"
              placeholder="Введите возраст ребёнка"
              value={age}
              onChange={(e) => onAgeChange(e.target.value)}
              min={2}
              max={17}
              style={{ borderColor: !age ? "#fcd89a" : undefined }}
            />
            {!age && (
              <span
                style={{
                  fontSize: 11,
                  color: "#e67e22",
                  marginTop: 4,
                  display: "block",
                }}
              >
                Возраст влияет на калибровку результатов по нормам развития
              </span>
            )}
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
            {error}
            {error.includes("Failed to fetch") && (
              <div style={{ marginTop: 8, fontSize: 13, color: "#636e72" }}>
                Запустите сервер:{" "}
                <code>py -3.11 -m uvicorn server:app --reload</code>
              </div>
            )}
          </div>
        )}

        <button
          className="btn-primary"
          onClick={() => onAnalyze(getMode())}
          disabled={
            !previewUrl ||
            !age ||
            loading ||
            (tab !== "opencv" && !isAvailable(tab))
          }
          style={{
            background:
              loading ||
              !previewUrl ||
              !age ||
              (tab !== "opencv" && !isAvailable(tab))
                ? "#b2bec3"
                : activeColor,
          }}
        >
          {loading ? (
            <>
              <span className="spin">&#8635;</span> {loadingMsg()}
            </>
          ) : (
            `Запустить анализ — ${TAB_META[tab].label}${tab === "groq" && hybrid ? " + OpenCV" : ""}`
          )}
        </button>
      </div>
    </div>
  );
}
