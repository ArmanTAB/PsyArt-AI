import { OverallState } from "../../types/analysis";

interface Props {
  status: OverallState;
}

const STATUS_MAP: Record<OverallState, { bg: string; label: string }> = {
  норма: { bg: "#00b894", label: "✓ Норма" },
  требует_внимания: { bg: "#fdcb6e", label: "⚠ Требует внимания" },
  требует_консультации: { bg: "#e17055", label: "⚡ Нужна консультация" },
};

export default function StatusBadge({ status }: Props) {
  const s = STATUS_MAP[status] ?? STATUS_MAP["норма"];
  return (
    <span
      style={{
        background: s.bg,
        color: "#fff",
        padding: "4px 14px",
        borderRadius: 20,
        fontSize: 13,
        fontWeight: 700,
      }}
    >
      {s.label}
    </span>
  );
}
