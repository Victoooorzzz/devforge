"use client";
import Image from "next/image";
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
    <div className="min-h-screen flex flex-col md:flex-row" style={{ backgroundColor: "var(--color-bg)" }}>
      {/* Sidebar */}
      <aside className="w-full md:w-56 md:flex-shrink-0 flex flex-col border-b md:border-b-0 md:border-r" style={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <div className="h-16 flex items-center px-5 border-b" style={{ borderColor: "var(--color-border)" }}>
          <Link href="/" className="flex items-center gap-3">
            <Image src="/devforge-logo-white.svg" alt="DevForge" width={98} height={20} className="h-5 w-auto" />
            <span className="text-base font-bold border-l border-white/10 pl-3">
              Feedback<span style={{ color: "var(--color-accent)" }}>Lens</span>
            </span>
          </Link>
        </div>
        <nav className="flex flex-wrap gap-2 md:block md:flex-1 px-3 py-3 md:py-4 md:space-y-1">
          <Link
            href="/dashboard"
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap"
            style={{ color: "var(--color-text)", backgroundColor: "var(--color-surface-raised)" }}
          >
            <span style={{ color: "var(--color-accent)" }}>◈</span> Feedback
          </Link>
        </nav>
        <div className="px-3 pb-3 md:pb-4 md:border-t md:pt-4" style={{ borderColor: "var(--color-border)" }}>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 w-fit md:w-full text-sm rounded-md transition-colors"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <span>→</span> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-6 md:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
