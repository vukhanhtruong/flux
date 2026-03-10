import { useEffect, useState } from "react";
import { Target } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Goal } from "../types";

export function Goals() {
  const { profile } = useProfile();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchGoals() {
    try {
      const data = await api.listGoals(USER_ID);
      setGoals(data);
    } catch (error) {
      console.error("Failed to fetch goals:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchGoals();
  }, []);

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Goals</h1>
          <p className="text-slate-400">Track progress toward your financial milestones.</p>
        </div>
      </div>

      {goals.length === 0 ? (
        <div className="glass-card p-12 md:p-16 lg:p-20 text-center">
          <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Target className="w-10 h-10 text-slate-500" />
          </div>
          <p className="text-slate-500 text-lg italic">No goals yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:gap-6 lg:gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal) => {
            const current = parseFloat(goal.current_amount);
            const target = parseFloat(goal.target_amount);
            const pct = target > 0 ? Math.min(100, (current / target) * 100) : 0;

            return (
              <div
                key={goal.id}
                className="glass-card p-4 md:p-6 lg:p-8 flex flex-col h-full hover:border-white/20 transition-all group"
              >
                <div className="flex items-start justify-between mb-6">
                  <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">
                    {goal.name}
                  </h3>
                </div>

                <div className="flex-1 space-y-4">
                  <div className="flex justify-between items-end pb-1">
                    <span className="text-2xl font-bold text-white">
                      {formatCurrency(current, profile.currency, profile.locale)}
                    </span>
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-widest whitespace-nowrap">
                      of {formatCurrency(target, profile.currency, profile.locale).replace(/\s/g, '\u00A0')}
                    </span>
                  </div>

                  <div className="h-4 w-full rounded-full bg-white/5 overflow-hidden border border-white/5 p-0.5">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${pct >= 100
                        ? "bg-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.5)]"
                        : "bg-primary shadow-[0_0_15px_rgba(245,158,11,0.5)]"
                        }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-xs font-bold uppercase tracking-widest text-slate-500 italic">
                    <span>{pct.toFixed(1)}% Completed</span>
                    {goal.deadline && (
                      <span className="text-slate-400">
                        Due {formatDate(goal.deadline, profile.locale, profile.timezone)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-6 border-t border-white/5">
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
