"use client";
import { useEffect, useState } from "react";
import { auth } from "@devforge/core";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Home, Settings, LogOut } from "lucide-react";

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
    <div className="dashboard-shell min-h-screen bg-black flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="dashboard-sidebar w-full overflow-hidden md:w-64 md:shrink-0 border-b md:border-b-0 md:border-r border-white/5 p-4 md:p-6 flex flex-col md:min-h-screen">
        <Link href="/" className="flex min-w-0 items-center gap-3 mb-4 md:mb-8">
          <Image src="/devforge-logo-white.svg" alt="DevForge" width={96} height={20} className="h-5 w-auto shrink-0" style={{ width: "auto", height: "auto" }} />
          <span className="block min-w-0 truncate text-base font-bold tracking-tight border-l border-white/20 pl-3">
            File<span className="text-accent">Cleaner</span>
          </span>
        </Link>

        <nav className="flex flex-wrap gap-2 md:block md:space-y-1 md:flex-1">
          <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 rounded-lg bg-accent/10 text-white text-sm font-medium whitespace-nowrap">
            <Home size={18} /> Overview
          </Link>
          <Link href="/dashboard/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 text-sm font-medium whitespace-nowrap">
            <Settings size={18} /> Settings
          </Link>
        </nav>

        <button 
          onClick={() => { auth.logout(); router.push("/login"); }}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-neutral-400 hover:text-red-400 hover:bg-red-400/5 text-sm font-medium mt-3 md:mt-auto w-fit md:w-auto"
        >
          <LogOut size={18} /> Logout
        </button>
      </aside>

      {/* Main Content */}
      <main className="dashboard-main flex-1 min-w-0 p-4 md:p-8 overflow-auto">
        {children}
      </main>
    </div>
  );
}
