interface PriceChartPoint {
  label: string;
  value: number;
}

interface PriceChartProps {
  points: PriceChartPoint[];
  height?: number;
}

export function PriceChart({ points, height = 160 }: PriceChartProps) {
  const width = 520;
  const padding = 24;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const coords = points.map((point, index) => {
    const x = padding + (index / Math.max(points.length - 1, 1)) * usableWidth;
    const y = padding + (1 - (point.value - min) / range) * usableHeight;
    return { ...point, x, y };
  });
  const path = coords.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");

  return (
    <div className="surface-card-raised border border-white/10 p-4">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label="Price history chart">
        <line x1={padding} x2={width - padding} y1={height - padding} y2={height - padding} stroke="rgba(255,255,255,0.12)" />
        <line x1={padding} x2={padding} y1={padding} y2={height - padding} stroke="rgba(255,255,255,0.12)" />
        <path d={path} fill="none" stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {coords.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="4" fill="var(--color-accent)" />
            <text x={point.x} y={height - 6} textAnchor="middle" fontSize="10" fill="#A3A3A3">
              {point.label}
            </text>
          </g>
        ))}
      </svg>
      <div className="mt-3 flex items-center justify-between text-xs" style={{ color: "var(--color-text-secondary)" }}>
        <span>${min.toFixed(2)}</span>
        <span>${max.toFixed(2)}</span>
      </div>
    </div>
  );
}
