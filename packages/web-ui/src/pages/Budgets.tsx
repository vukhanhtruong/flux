import { useEffect, useState } from "react";
import { Wallet } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency } from "../lib/format";
import type { Budget } from "../types";

export function Budgets() {
  const { profile } = useProfile();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [spending, setSpending] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  async function fetchBudgets() {
    try {
      const now = new Date();
      const startDate = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split("T")[0];
      const endDate = now.toISOString().split("T")[0];

      const [budgetsData, spendingData] = await Promise.all([
        api.listBudgets(USER_ID),
        api.getSpendingReport(USER_ID, startDate, endDate),
      ]);

      setBudgets(budgetsData);

      const breakdown: Record<string, number> = {};
      spendingData.category_breakdown.forEach((row) => {
        breakdown[row.category.toLowerCase()] = parseFloat(row.total);
      });
      setSpending(breakdown);
    } catch (error) {
      console.error("Failed to fetch budgets or spending:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchBudgets();
  }, []);

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Budgets</h1>
          <p className="text-slate-400">View budget limits for your spending categories.</p>
        </div>
      </div>

      {budgets.length === 0 ? (
        <div className="glass-card p-20 text-center">
          <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Wallet className="w-10 h-10 text-slate-500" />
          </div>
          <p className="text-slate-500 text-lg italic">
            No budgets set yet.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {budgets.map((budget) => {
            const spent = spending[budget.category.toLowerCase()] || 0;
            const limit = parseFloat(budget.monthly_limit);
            const percent = limit > 0 ? Math.min(100, (spent / limit) * 100) : 0;
            const isOver = spent > limit;

            return (
              <div
                key={budget.id}
                className={`glass-card p-8 flex flex-col hover:border-white/20 transition-all group ${isOver ? "border-red-500/50" : ""
                  }`}
              >
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">
                      {budget.category}
                    </h3>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-3xl font-black text-white">
                        {formatCurrency(budget.monthly_limit, profile.currency, profile.locale)}
                      </span>
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                        /mo
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto space-y-3">
                  <div className="flex justify-between items-end mb-1">
                    <span className="text-xs font-bold text-slate-400">
                      Spent: {formatCurrency(spent, profile.currency, profile.locale)}
                    </span>
                    <span className={`text-xs font-black ${isOver ? "text-red-400" : "text-primary"}`}>
                      {percent.toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2.5 w-full rounded-full bg-white/5 overflow-hidden border border-white/5">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${isOver ? "bg-red-500" : "bg-primary"
                        }`}
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-tighter text-slate-500">
                    <span>{isOver ? "Over Budget" : `${formatCurrency(limit - spent, profile.currency, profile.locale)} remaining`}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
