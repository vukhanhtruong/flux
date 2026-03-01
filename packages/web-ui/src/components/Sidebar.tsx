import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowRightLeft,
  Wallet,
  Target,
  CalendarRange,
  BarChart3,
  Settings,
  Flame,
  Github,
  Coffee,
} from "lucide-react";
import { SHOW_PROMO_CARD } from "../lib/constants";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Transactions", href: "/transactions", icon: ArrowRightLeft },
  { name: "Budgets", href: "/budgets", icon: Wallet },
  { name: "Goals", href: "/goals", icon: Target },
  { name: "Subscriptions", href: "/subscriptions", icon: CalendarRange },
  { name: "Reports", href: "/reports", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex flex-col w-64 h-screen border-r bg-dark border-white/5">
      <div className="flex items-center px-8 h-20">
        <div className="flex gap-2 items-center">
          <div className="p-2 rounded-xl bg-primary/10">
            <Flame className="w-6 h-6 text-primary fill-primary" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">
            flux
          </span>
        </div>
      </div>
      <nav className="flex-1 py-6 px-4 space-y-1.5">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 group ${
                isActive
                  ? "bg-primary text-dark shadow-lg shadow-primary/20"
                  : "text-slate-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon
                className={`w-5 h-5 ${isActive ? "text-dark" : "text-slate-400 group-hover:text-white"}`}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>
      {SHOW_PROMO_CARD && (
        <div className="p-4">
          <div className="p-4 bg-gradient-to-br to-transparent border glass-card from-primary/10 border-white/5">
            <p className="mb-3 font-black tracking-widest uppercase text-[10px] text-primary">
              Support flux
            </p>
            <div className="space-y-2">
              <a
                href="https://github.com/vukhanhtruong/flux"
                target="_blank"
                rel="noopener noreferrer"
                className="flex gap-2.5 items-center text-xs transition-colors hover:text-white text-slate-400 group/link"
              >
                <div className="p-1.5 rounded-lg transition-all bg-white/5 group-hover/link:bg-primary/20 group-hover/link:text-primary">
                  <Github size={14} />
                </div>
                <span>Star on GitHub</span>
              </a>
              <a
                href="https://buymeacoffee.com/gnourt"
                target="_blank"
                rel="noopener noreferrer"
                className="flex gap-2.5 items-center text-xs transition-colors hover:text-white text-slate-400 group/link"
              >
                <div className="p-1.5 rounded-lg transition-all bg-white/5 group-hover/link:bg-amber-400/20 group-hover/link:text-amber-400">
                  <Coffee size={14} />
                </div>
                <span>Buy me a coffee</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
