interface JsonViewerProps {
  value: unknown;
  title?: string;
}

export function JsonViewer({ value, title }: JsonViewerProps) {
  return (
    <div className="surface-card-raised overflow-hidden border border-white/10">
      {title ? (
        <div className="border-b border-white/10 px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
          {title}
        </div>
      ) : null}
      <pre className="max-h-80 overflow-auto p-4 text-xs leading-relaxed" style={{ color: "var(--color-text)" }}>
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
