import { useCallback, useRef, useState } from "react";

interface Props {
  previewUrl: string | null;
  onFile: (file: File) => void;
  onClear: () => void;
}

export default function UploadZone({ previewUrl, onFile, onClear }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f?.type.startsWith("image/")) onFile(f);
    },
    [onFile],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        className={`upload-zone${dragOver ? " drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
      >
        {previewUrl ? (
          <img
            src={previewUrl}
            alt="preview"
            style={{
              maxHeight: 280,
              maxWidth: "100%",
              borderRadius: 10,
              objectFit: "contain",
            }}
          />
        ) : (
          <>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🖼️</div>
            <p style={{ color: "#636e72", fontSize: 15 }}>
              Перетащите рисунок сюда
            </p>
            <p style={{ color: "#b2bec3", fontSize: 13, marginTop: 4 }}>
              или нажмите для выбора · PNG / JPG / WEBP
            </p>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          aria-label="Загрузить рисунок"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
          }}
        />
      </div>

      {previewUrl && (
        <button
          style={{
            background: "none",
            border: "1px solid #e0dbd5",
            color: "#636e72",
            padding: "8px 16px",
            borderRadius: 8,
            fontSize: 13,
            cursor: "pointer",
            alignSelf: "flex-start",
          }}
          onClick={onClear}
        >
          ✕ Удалить
        </button>
      )}
    </div>
  );
}
