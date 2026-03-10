import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowRightLeft,
  Wallet,
  Target,
  CalendarRange,
  Landmark,
  BarChart3,
  Settings,
  Flame,
  Github,
  Coffee,
  X,
} from "lucide-react";
import { SHOW_PROMO_CARD } from "../lib/constants";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Transactions", href: "/transactions", icon: ArrowRightLeft },
  { name: "Budgets", href: "/budgets", icon: Wallet },
  { name: "Goals", href: "/goals", icon: Target },
  { name: "Subscriptions", href: "/subscriptions", icon: CalendarRange },
  { name: "Assets", href: "/assets", icon: Landmark },
  { name: "Reports", href: "/reports", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const [showPromo, setShowPromo] = useState(true);

  // Close sidebar on route change on mobile
  useEffect(() => {
    onClose();
  }, [location.pathname]);

  // Lock body scroll when sidebar is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
    return () => {
      document.body.style.overflow = "auto";
    }
  }, [isOpen]);

  return (
    <>
      {/* Mobile Overlay */}
      <div 
        className={`fixed inset-0 bg-black/60 z-30 md:hidden transition-opacity duration-300 ${isOpen ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={onClose}
      />
      
      {/* Sidebar Content */}
      <div className={`fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${isOpen ? "translate-x-0" : "-translate-x-full"} flex flex-col h-screen border-r bg-dark border-white/5`}>
        <div className="flex items-center justify-between px-6 h-16 md:px-8 md:h-20 shrink-0">
          <div className="flex gap-2 items-center">
            <div className="p-2 rounded-xl bg-primary/10">
              <Flame className="w-6 h-6 text-primary fill-primary" />
            </div>
            <span className="text-2xl font-bold tracking-tight text-white">
              flux
            </span>
          </div>
          <button 
            className="md:hidden p-2 -mr-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-slate-400 hover:text-white"
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1.5 custom-scrollbar">
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
                <Icon
                  className={`w-5 h-5 shrink-0 ${isActive ? "text-dark" : "text-slate-400 group-hover:text-white"}`}
                />
                <span className="truncate">{item.name}</span>
              </Link>
            );
          })}
        </nav>
        {SHOW_PROMO_CARD && showPromo && (
          <div className="p-4 shrink-0">
            <div className="relative p-4 bg-gradient-to-br to-transparent border glass-card from-primary/10 border-white/5">
              <button
                onClick={() => setShowPromo(false)}
                className="absolute top-2 right-2 p-1 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                title="Hide"
              >
                <X size={14} />
              </button>
              <p className="pr-4 mb-3 font-black tracking-widest uppercase text-[10px] text-primary">
                Support flux
              </p>
              <div className="space-y-2">
                <a
                  href="https://github.com/vukhanhtruong/flux"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex gap-2.5 items-center text-xs transition-colors hover:text-white text-slate-400 group/link"
                >
                  <div className="p-1.5 shrink-0 rounded-lg transition-all bg-white/5 group-hover/link:bg-primary/20 group-hover/link:text-primary">
                    <Github size={14} />
                  </div>
                  <span className="truncate">Star on GitHub</span>
                </a>
                <a
                  href="https://buymeacoffee.com/gnourt"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex gap-2.5 items-center text-xs transition-colors hover:text-white text-slate-400 group/link"
                >
                  <div className="p-1.5 shrink-0 rounded-lg transition-all bg-white/5 group-hover/link:bg-amber-400/20 group-hover/link:text-amber-400">
                    <Coffee size={14} />
                  </div>
                  <span className="truncate">Buy me a coffee</span>
                </a>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
