import { TABS } from "../../constants";

interface Props {
  activeTab: number;
  onTabChange: (index: number) => void;
}

export default function Header({ activeTab, onTabChange }: Props) {
  return (
    <div
      style={{
        background: "#fff",
        borderBottom: "1px solid #ede9e4",
        padding: "0 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 64,
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: "linear-gradient(135deg, #6c5ce7, #a29bfe)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 15,
            fontWeight: 700,
            color: "#fff",
            fontFamily: "DM Serif Display, serif",
          }}
        >
          AM
        </div>
        <div>
          <div
            style={{
              fontFamily: "DM Serif Display, serif",
              fontSize: 17,
              color: "#2d3436",
              lineHeight: 1.2,
            }}
          >
            АртМинд
          </div>
          <div
            style={{
              fontSize: 11,
              color: "#b2bec3",
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            Психоэмоциональный анализ
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 4 }}>
        {TABS.map((t, i) => (
          <button
            key={t}
            className={`tab${activeTab === i ? " active" : ""}`}
            onClick={() => onTabChange(i)}
          >
            {t}
          </button>
        ))}
      </div>

      <div
        style={{
          fontSize: 13,
          color: "#b2bec3",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span
          style={{
            background: "#6c5ce7",
            width: 8,
            height: 8,
            borderRadius: "50%",
            display: "inline-block",
          }}
        />
        OpenCV + LLM Vision
      </div>
    </div>
  );
}
