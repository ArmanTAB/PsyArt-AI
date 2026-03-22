export default function AboutPage() {
  return (
    <div className="fade-in" style={{ maxWidth: 680 }}>
      <h2
        style={{
          fontFamily: "DM Serif Display, serif",
          fontSize: 28,
          color: "#2d3436",
          marginBottom: 24,
        }}
      >
        Архитектура системы
      </h2>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 18,
            marginBottom: 16,
          }}
        >
          Стек технологий
        </h3>
        {(
          [
            ["Бэкенд", "Python 3.11 + FastAPI"],
            ["Компьютерное зрение", "OpenCV 4.x (8 модулей)"],
            ["Кластеризация", "scikit-learn KMeans"],
            ["Обработка изображений", "Pillow (PIL)"],
            ["LLM Vision", "Groq API (LLaMA-4 Scout)"],
            ["База данных", "PostgreSQL + SQLAlchemy"],
            ["Фронтенд", "React 18 + Vite + TypeScript"],
          ] as [string, string][]
        ).map(([k, v]) => (
          <div key={k} className="stat-row">
            <span style={{ color: "#636e72", fontSize: 14 }}>{k}</span>
            <span
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 13,
                fontWeight: 600,
                color: "#2d3436",
              }}
            >
              {v}
            </span>
          </div>
        ))}
      </div>

      <div
        className="card"
        style={{
          marginBottom: 16,
          background: "#f8f5ff",
          borderColor: "#e2d9f3",
        }}
      >
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 18,
            marginBottom: 16,
            color: "#6c5ce7",
          }}
        >
          Гибридная модель анализа
        </h3>
        {[
          {
            step: "1",
            title: "Загрузка и нормализация",
            desc: "PIL — resize 512x512, конвертация в BGR и HSV",
          },
          {
            step: "2",
            title: "OpenCV-анализ (8 модулей)",
            desc: "Люшер (цвет — эмоции), Маховер (зоны), линии, сигнатуры радости, объекты, Haar-каскады, LBP-текстура, FFT-спектр",
          },
          {
            step: "3",
            title: "LLM Vision (Groq)",
            desc: "Chain-of-Thought промпт — визуальное описание — психологическая интерпретация — структурированный JSON",
          },
          {
            step: "4",
            title: "Гибридная агрегация",
            desc: "LLM 65% (семантика, символика) + OpenCV 35% (точные метрики цвета, линий, зон)",
          },
          {
            step: "5",
            title: "Возрастная калибровка и отчёт",
            desc: "Коррекция по возрастным нормам (3-5, 6-8, 9-12, 13-18 лет); контекст-адаптация; генерация отчёта",
          },
        ].map(({ step, title, desc }) => (
          <div
            key={step}
            style={{
              display: "flex",
              gap: 12,
              alignItems: "flex-start",
              marginBottom: 14,
            }}
          >
            <span
              style={{
                minWidth: 28,
                height: 28,
                background: "#6c5ce7",
                color: "#fff",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 13,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {step}
            </span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, color: "#2d3436" }}>
                {title}
              </div>
              <div style={{ fontSize: 13, color: "#636e72" }}>{desc}</div>
            </div>
          </div>
        ))}
      </div>

      <div
        className="card"
        style={{
          marginBottom: 16,
          background: "#fff8f0",
          borderColor: "#fcd89a",
        }}
      >
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 18,
            marginBottom: 12,
            color: "#e67e22",
          }}
        >
          Психологическая база
        </h3>
        {[
          {
            method: "Тест Люшера",
            desc: "Цвет — эмоции (10 цветовых групп с весовыми коэффициентами)",
          },
          {
            method: "Методика Маховер",
            desc: "Зональный анализ листа (верх/низ/лево/право/центр)",
          },
          {
            method: "Арт-терапия Копытина",
            desc: "Общие принципы интерпретации детского рисунка",
          },
        ].map(({ method, desc }) => (
          <div key={method} style={{ marginBottom: 10 }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: "#2d3436" }}>
              {method}
            </span>
            <span style={{ fontSize: 13, color: "#636e72" }}> — {desc}</span>
          </div>
        ))}
        <div style={{ marginTop: 12, fontSize: 13, color: "#636e72" }}>
          5 эмоций: радость, грусть, тревога, агрессия, спокойствие. 3 итоговых
          состояния: норма / требует внимания / требует консультации.
        </div>
      </div>

      <div
        className="card"
        style={{ background: "#f0fff4", borderColor: "#c3e6cb" }}
      >
        <h3
          style={{
            fontFamily: "DM Serif Display, serif",
            fontSize: 18,
            marginBottom: 12,
            color: "#2e7d32",
          }}
        >
          Запуск
        </h3>
        <pre
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 13,
            color: "#2d3436",
            lineHeight: 1.8,
            background: "#f5f5f5",
            padding: 16,
            borderRadius: 10,
            overflow: "auto",
          }}
        >{`# Бэкенд
cd core
py -3.11 -m pip install -r requirements.txt
py -3.11 -m uvicorn server:app --reload --port 8000

# Фронтенд
cd interface
npm install
npm run dev

# Открыть: http://localhost:5173`}</pre>
      </div>
    </div>
  );
}
