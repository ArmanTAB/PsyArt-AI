import { Emotion } from "../../types/analysis";
import { EMOTIONS } from "../../constants";

interface Props extends Emotion {}

export default function EmotionBar({ name, intensity, evidence }: Props) {
  const em = EMOTIONS[name] ?? { color: "#ccc", icon: "●" };

  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 5,
          alignItems: "center",
        }}
      >
        <span
          style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 15,
            color: "#2d3436",
          }}
        >
          {em.icon} {name}
        </span>
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 12,
            fontWeight: 700,
            color: em.color,
            background: em.color + "22",
            padding: "2px 8px",
            borderRadius: 20,
          }}
        >
          {intensity}%
        </span>
      </div>
      <div
        style={{
          height: 8,
          background: "#f0f0f0",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${intensity}%`,
            background: `linear-gradient(90deg, ${em.color}88, ${em.color})`,
            borderRadius: 8,
            transition: "width 1.2s cubic-bezier(.4,0,.2,1)",
          }}
        />
      </div>
      {evidence && (
        <p
          style={{
            fontSize: 12,
            color: "#636e72",
            marginTop: 4,
            fontStyle: "italic",
          }}
        >
          {evidence}
        </p>
      )}
    </div>
  );
}
