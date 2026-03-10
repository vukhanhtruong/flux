import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Menu, Flame } from "lucide-react";

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-dark text-slate-50 font-sans overflow-hidden">
      {/* Mobile top nav */}
      <div className="md:hidden flex flex-shrink-0 items-center justify-between px-4 h-16 border-b border-white/5 bg-dark fixed top-0 left-0 right-0 z-20">
        <div className="flex gap-2 items-center">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Flame className="w-5 h-5 text-primary fill-primary" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">
            flux
          </span>
        </div>
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 -mr-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-slate-400 hover:text-white transition-colors"
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <main className="flex-1 overflow-y-auto scroll-smooth pt-16 md:pt-0">
        <div className="container mx-auto p-4 md:p-6 lg:p-8 animate-in fade-in duration-700">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
