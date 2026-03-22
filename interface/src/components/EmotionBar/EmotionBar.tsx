import { useState } from "react";
import { Emotion, EvidenceChain } from "../../types/analysis";
import { EMOTIONS } from "../../constants";

interface Props extends Emotion {
  chain?: EvidenceChain;
}

export default function EmotionBar({
  name,
  intensity,
  evidence,
  chain,
}: Props) {
  const em = EMOTIONS[name] ?? { color: "#ccc", label: name };
  const [expanded, setExpanded] = useState(false);
  const hasChain = chain && chain.modules.length > 0;

  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 5,
          alignItems: "center",
          cursor: hasChain ? "pointer" : "default",
        }}
        onClick={() => hasChain && setExpanded(!expanded)}
      >
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 15,
            color: "#2d3436",
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: em.color,
              display: "inline-block",
              flexShrink: 0,
            }}
          />
          {em.label}
          {hasChain && (
            <span
              style={{
                fontSize: 11,
                color: "#b2bec3",
                transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.2s",
                display: "inline-block",
              }}
            >
              &#9662;
            </span>
          )}
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

      {evidence && !expanded && (
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

      {expanded && hasChain && (
        <div
          style={{
            marginTop: 8,
            padding: "12px 14px",
            background: "#fafafa",
            borderRadius: 10,
            border: "1px solid #f0ece8",
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "#636e72",
              textTransform: "uppercase",
              letterSpacing: 0.5,
              marginBottom: 8,
            }}
          >
            Вклад модулей в оценку
          </div>
          {chain.modules.map((mod) => {
            const maxWeighted = Math.max(
              ...chain.modules.map((m) => m.weighted),
              1,
            );
            const barWidth = (mod.weighted / maxWeighted) * 100;
            return (
              <div key={mod.name} style={{ marginBottom: 6 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12,
                    marginBottom: 2,
                  }}
                >
                  <span style={{ color: "#4a4a4a" }}>{mod.name}</span>
                  <span
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 11,
                      color: "#636e72",
                    }}
                  >
                    {mod.raw} x {mod.weight} = {mod.weighted}
                  </span>
                </div>
                <div
                  style={{
                    height: 4,
                    background: "#e8e8e8",
                    borderRadius: 4,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${barWidth}%`,
                      background: em.color + "aa",
                      borderRadius: 4,
                      transition: "width 0.6s ease",
                    }}
                  />
                </div>
              </div>
            );
          })}
          <div
            style={{
              marginTop: 8,
              paddingTop: 8,
              borderTop: "1px solid #e8e8e8",
              display: "flex",
              justifyContent: "space-between",
              fontSize: 12,
              fontWeight: 700,
              color: "#2d3436",
            }}
          >
            <span>Итого (до коррекций)</span>
            <span style={{ fontFamily: "JetBrains Mono, monospace" }}>
              {chain.total}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
