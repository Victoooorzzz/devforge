import type { DevForgeProduct } from "@devforge/core";

interface FeatureComparisonProps {
  product: DevForgeProduct;
}

export function FeatureComparison({ product }: FeatureComparisonProps) {
  return (
    <div className="overflow-hidden rounded-md border border-white/10">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead style={{ backgroundColor: "rgba(255,255,255,0.04)" }}>
            <tr>
              <th className="px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
                Feature
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
                Free
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>
                Pro
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
                Team
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {product.comparison.map((row) => (
              <tr key={row.feature} className="bg-black/20">
                <td className="px-4 py-3 font-medium" style={{ color: "var(--color-text)" }}>
                  {row.feature}
                </td>
                <td className="px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>
                  {row.free}
                </td>
                <td className="px-4 py-3" style={{ color: "var(--color-text)" }}>
                  {row.pro}
                </td>
                <td className="px-4 py-3" style={{ color: "var(--color-text)" }}>
                  {row.team}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
