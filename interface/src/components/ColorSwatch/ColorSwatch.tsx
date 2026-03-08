interface Props {
  hex: string;
}

export default function ColorSwatch({ hex }: Props) {
  return (
    <div
      title={hex}
      style={{
        width: 28,
        height: 28,
        borderRadius: 6,
        background: hex,
        flexShrink: 0,
        border: "2px solid #fff",
        boxShadow: "0 2px 6px rgba(0,0,0,.15)",
      }}
    />
  );
}
