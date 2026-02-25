import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function Layout() {
  return (
    <div className="flex h-screen bg-dark text-slate-50 font-sans">
      <Sidebar />
      <main className="flex-1 overflow-y-auto scroll-smooth">
        <div className="container mx-auto p-8 animate-in fade-in duration-700">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
