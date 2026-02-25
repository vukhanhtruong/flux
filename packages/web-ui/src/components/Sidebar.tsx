import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowRightLeft,
  Wallet,
  Target,
  CalendarRange,
  BarChart3,
  Settings,
  Flame
} from "lucide-react";

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
    <div className="flex h-screen w-64 flex-col bg-dark border-r border-white/5">
      <div className="flex h-20 items-center px-8">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-primary/10 rounded-xl">
            <Flame className="w-6 h-6 text-primary fill-primary" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">flux</span>
        </div>
      </div>
      <nav className="flex-1 space-y-1.5 px-4 py-6">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 group ${isActive
                  ? "bg-primary text-dark shadow-lg shadow-primary/20"
                  : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? "text-dark" : "text-slate-400 group-hover:text-white"}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>
      <div className="p-4">
        <div className="glass-card p-4 bg-gradient-to-br from-primary/10 to-transparent">
          <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">Pro Plan</p>
          <p className="text-xs text-slate-400 mb-3">Unlock advanced analytics and crypto tracking.</p>
          <button className="w-full btn-primary text-xs py-2">Upgrade Now</button>
        </div>
      </div>
    </div>
  );
}
