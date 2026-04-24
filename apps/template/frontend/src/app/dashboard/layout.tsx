"use client";
import { useEffect, useState } from "react";
import { DashboardShell } from "@devforge/ui";
import { apiClient, removeToken } from "@devforge/core";
import { product } from "@/config/product";

const navIcons = {
  dashboard: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/></svg>,
  settings: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="10" cy="10" r="3"/><path d="M10 1v2M10 17v2M1 10h2M17 10h2"/></svg>,
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<{ email: string } | null>(null);

  useEffect(() => {
    apiClient.get<{ email: string }>("/auth/me").then(({ data }) => setUser(data)).catch(() => { window.location.href = "/login"; });
  }, []);

  if (!user) return <div className="min-h-screen" style={{ backgroundColor: "var(--color-bg)" }} />;

  const navItems = product.dashboardNav.map((item) => ({
    ...item,
    icon: item.href.includes("settings") ? navIcons.settings : navIcons.dashboard,
    active: typeof window !== "undefined" && window.location.pathname === item.href,
  }));

  return (
    <DashboardShell productName={product.name} navItems={navItems} userName={user.email.split("@")[0]} userEmail={user.email} onLogout={() => { removeToken(); window.location.href = "/login"; }}>
      {children}
    </DashboardShell>
  );
}
