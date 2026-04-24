export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-2" style={{ color: "var(--color-text)" }}>Dashboard</h1>
      <p className="text-sm mb-8" style={{ color: "var(--color-text-secondary)" }}>Welcome back. Your workspace is ready.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {["Total Items", "Active", "Processed"].map((label, i) => (
          <div key={label} className="p-6 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
            <p className="text-xs font-medium uppercase tracking-wide mb-1" style={{ color: "var(--color-text-secondary)" }}>{label}</p>
            <p className="text-3xl font-bold font-mono" style={{ color: "var(--color-text)" }}>{[0, 0, 0][i]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
