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
            ["Компьютерное зрение", "OpenCV 4.x"],
            ["Кластеризация", "scikit-learn KMeans"],
            ["Обработка изображений", "Pillow (PIL)"],
            ["Фронтенд", "React 18 + Vite + TypeScript"],
            ["Внешние AI-сервисы", "— не используются —"],
          ] as [string, string][]
        ).map(([k, v]) => (
          <div key={k} className="stat-row">
            <span style={{ color: "#636e72", fontSize: 14 }}>{k}</span>
            <span
              style={{
                fontFamily: v.includes("—")
                  ? "inherit"
                  : "JetBrains Mono, monospace",
                fontSize: 13,
                fontWeight: 600,
                color: v.includes("—") ? "#00b894" : "#2d3436",
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
            desc: "PIL → resize 512×512, конвертация в BGR и HSV",
          },
          {
            step: "2",
            title: "Цветовой анализ",
            desc: "K-Means (k=5) для доминирующих цветов; HSV-маски для 9 цветовых групп",
          },
          {
            step: "3",
            title: "Анализ композиции",
            desc: "Моменты OpenCV для центра масс; контуры Canny; подсчёт объектов",
          },
          {
            step: "4",
            title: "Экспертные правила (Люшер)",
            desc: "Таблицы цвет → эмоция с весами; модификаторы яркости и насыщенности",
          },
          {
            step: "5",
            title: "Синтез и отчёт",
            desc: "Нормализация баллов 0–100; генерация текстового портрета; оценка рисков",
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
          🚀 Запуск
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
        ></pre>
      </div>
    </div>
  );
}
