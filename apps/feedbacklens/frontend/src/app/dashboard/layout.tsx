"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { isAuthenticated, removeToken } from "@devforge/core";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  const handleLogout = () => {
    removeToken();
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: "var(--color-bg)" }}>
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col border-r" style={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <div className="h-16 flex items-center px-5 border-b" style={{ borderColor: "var(--color-border)" }}>
          <Link href="/" className="text-base font-bold" style={{ color: "var(--color-accent)" }}>
            FeedbackLens
          </Link>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          <Link
            href="/dashboard"
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors"
            style={{ color: "var(--color-text)", backgroundColor: "var(--color-surface-raised)" }}
          >
            <span style={{ color: "var(--color-accent)" }}>◈</span> Feedback
          </Link>
        </nav>
        <div className="px-3 pb-4 border-t pt-4" style={{ borderColor: "var(--color-border)" }}>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 w-full text-sm rounded-md transition-colors"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <span>→</span> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-8 py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
