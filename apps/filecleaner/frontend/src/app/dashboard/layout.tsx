"use client";
import { useEffect, useState } from "react";
import { auth } from "@devforge/core";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Home, Settings, LogOut, Layout } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [authorized, setAuthorized] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push("/login");
    } else {
      setAuthorized(true);
    }
  }, [router]);

  if (!authorized) return null;

  return (
    <div className="min-h-screen bg-black flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/5 p-6 flex flex-col">
        <Link href="/" className="flex items-center gap-3 mb-8">
          <img src="/devforge-logo-white.svg" alt="DevForge" className="h-5 w-auto" />
          <span className="text-xl font-bold tracking-tighter border-l border-white/20 pl-3">
            File<span className="text-accent">Cleaner</span>
          </span>
        </Link>

        <nav className="space-y-1 flex-1">
          <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 rounded-lg bg-accent/10 text-white text-sm font-medium">
            <Home size={18} /> Overview
          </Link>
          <Link href="/dashboard/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 text-sm font-medium">
            <Settings size={18} /> Settings
          </Link>
        </nav>

        <button 
          onClick={() => { auth.logout(); router.push("/login"); }}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-neutral-400 hover:text-red-400 hover:bg-red-400/5 text-sm font-medium mt-auto"
        >
          <LogOut size={18} /> Logout
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  );
}
