import { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import {
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  ShieldCheck,
  Target,
} from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency } from "../lib/format";
import type { SpendingReport, FinancialHealth } from "../types";

const COLORS = [
  "#3B82F6",
  "#10B981",
  "#F59E0B",
  "#EF4444",
  "#8B5CF6",
  "#EC4899",
  "#6366F1",
  "#14B8A6",
];

export function Reports() {
  const { profile } = useProfile();
  const [report, setReport] = useState<SpendingReport | null>(null);
  const [health, setHealth] = useState<FinancialHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const today = new Date().toISOString().split("T")[0];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];
  const [startDate, setStartDate] = useState(thirtyDaysAgo);
  const [endDate, setEndDate] = useState(today);

  async function fetchReports() {
    setLoading(true);
    setError(null);
    try {
      const [reportData, healthData] = await Promise.all([
        api.getSpendingReport(USER_ID, startDate, endDate),
        api.getFinancialHealth(USER_ID, startDate, endDate),
      ]);
      setReport(reportData);
      setHealth(healthData);
    } catch (err) {
      console.error("Failed to fetch reports:", err);
      setError(
        "Failed to load reports. Make sure you have transactions in this date range.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchReports();
  }, [startDate, endDate]);

  const pieData = report
    ? report.category_breakdown.map((row) => ({
        name: row.category,
        value: parseFloat(row.total),
      }))
    : [];

  return (
    <div className="space-y-10">
      <div className="flex flex-col gap-6 justify-between mb-10 md:flex-row md:items-center">
        <div>
          <h1 className="mb-2 text-4xl font-bold tracking-tight text-white">
            Reports
          </h1>
          <p className="text-slate-400">
            View spending reports and financial health insights.
          </p>
        </div>

        <div className="flex gap-4 items-center p-2 px-4 rounded-2xl border shadow-xl bg-white/5 border-white/10">
          <div
            className="flex flex-col cursor-pointer group"
            onClick={(e) =>
              (
                e.currentTarget.querySelector("input") as HTMLInputElement
              )?.showPicker()
            }
          >
            <label className="mb-1 font-black tracking-widest uppercase cursor-pointer text-[10px] text-slate-500">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="text-sm text-white bg-transparent transition-colors cursor-pointer outline-none [color-scheme:dark] accent-primary focus:text-primary"
            />
          </div>
          <div className="mx-2 w-px h-8 bg-white/10" />
          <div
            className="flex flex-col cursor-pointer group"
            onClick={(e) =>
              (
                e.currentTarget.querySelector("input") as HTMLInputElement
              )?.showPicker()
            }
          >
            <label className="mb-1 font-black tracking-widest uppercase cursor-pointer text-[10px] text-slate-500">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="text-sm text-white bg-transparent transition-colors cursor-pointer outline-none [color-scheme:dark] accent-primary focus:text-primary"
            />
          </div>
        </div>
      </div>

      {loading && (
        <div className="p-20 text-center animate-pulse glass-card">
          <p className="text-lg italic text-slate-500">
            Analyzing your finances...
          </p>
        </div>
      )}

      {error && (
        <div className="flex gap-4 items-center p-8 border-l-4 duration-500 glass-card border-l-red-500 animate-in fade-in">
          <div className="p-3 rounded-xl bg-red-500/10">
            <TrendingUp className="w-6 h-6 text-red-500 rotate-180" />
          </div>
          <p className="font-medium text-red-200">{error}</p>
        </div>
      )}

      {!loading && !error && report && (
        <>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="p-8 transition-all glass-card group hover:border-emerald-500/30">
              <div className="flex gap-3 items-center mb-4">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <ArrowUpRight className="w-5 h-5 text-emerald-500" />
                </div>
                <h3 className="font-bold tracking-widest uppercase text-[10px] text-slate-400">
                  Total Income
                </h3>
              </div>
              <p className="text-4xl font-black text-white transition-colors group-hover:text-emerald-400">
                {formatCurrency(
                  report.total_income,
                  profile.currency,
                  profile.locale,
                )}
              </p>
            </div>

            <div className="p-8 transition-all glass-card group hover:border-red-500/30">
              <div className="flex gap-3 items-center mb-4">
                <div className="p-2 rounded-lg bg-red-500/10">
                  <ArrowDownRight className="w-5 h-5 text-red-500" />
                </div>
                <h3 className="font-bold tracking-widest uppercase text-[10px] text-slate-400">
                  Total Expenses
                </h3>
              </div>
              <p className="text-4xl font-black text-white transition-colors group-hover:text-red-400">
                {formatCurrency(
                  report.total_expenses,
                  profile.currency,
                  profile.locale,
                )}
              </p>
            </div>

            <div
              className={`glass-card p-8 hover:border-primary/30 transition-all group ${
                parseFloat(report.net) >= 0
                  ? "border-primary/10"
                  : "border-red-500/10"
              }`}
            >
              <div className="flex gap-3 items-center mb-4">
                <div
                  className={`p-2 rounded-lg ${
                    parseFloat(report.net) >= 0
                      ? "bg-primary/10"
                      : "bg-red-500/10"
                  }`}
                >
                  <ShieldCheck
                    className={`w-5 h-5 ${
                      parseFloat(report.net) >= 0
                        ? "text-primary"
                        : "text-red-500"
                    }`}
                  />
                </div>
                <h3 className="font-bold tracking-widest uppercase text-[10px] text-slate-400">
                  Net Savings
                </h3>
              </div>
              <p
                className={`text-4xl font-black transition-colors ${
                  parseFloat(report.net) >= 0
                    ? "text-white group-hover:text-primary"
                    : "text-red-400"
                }`}
              >
                {formatCurrency(report.net, profile.currency, profile.locale)}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
            {pieData.length > 0 ? (
              <div className="p-10 glass-card">
                <div className="flex gap-3 items-center mb-8">
                  <div className="p-2 rounded-lg bg-violet-500/10">
                    <TrendingUp className="w-5 h-5 text-violet-500" />
                  </div>
                  <h2 className="text-xl font-bold tracking-tight text-white">
                    Spending by Category
                  </h2>
                </div>
                <div className="h-[400px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={80}
                        outerRadius={130}
                        paddingAngle={5}
                        dataKey="value"
                        nameKey="name"
                      >
                        {pieData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                            className="outline-none"
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e293b",
                          border: "1px solid rgba(255,255,255,0.1)",
                          borderRadius: "12px",
                          color: "#fff",
                        }}
                        itemStyle={{ color: "#fff" }}
                        formatter={(value) =>
                          formatCurrency(
                            Number(value),
                            profile.currency,
                            profile.locale,
                          )
                        }
                      />
                      <Legend
                        layout="vertical"
                        align="right"
                        verticalAlign="middle"
                        formatter={(value) => (
                          <span className="text-sm text-slate-300">
                            {value}
                          </span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              <div className="flex flex-col justify-center items-center p-10 text-center glass-card">
                <div className="p-4 mb-6 rounded-full bg-white/5">
                  <TrendingUp className="w-10 h-10 text-slate-500" />
                </div>
                <h2 className="mb-2 text-xl font-bold text-white">
                  No Spending Data
                </h2>
                <p className="text-slate-400 max-w-[280px]">
                  No expenses recorded in this period to show a category
                  breakdown.
                </p>
              </div>
            )}

            {health && (
              <div className="flex flex-col p-10 glass-card">
                <div className="flex gap-3 items-center mb-10">
                  <div className="p-2 rounded-lg bg-amber-500/10">
                    <Target className="w-5 h-5 text-amber-500" />
                  </div>
                  <h2 className="text-xl font-bold tracking-tight text-white">
                    Financial Health Insights
                  </h2>
                </div>

                <div className="grid flex-1 grid-cols-2 gap-8">
                  <div className="flex flex-col justify-center p-6 text-center rounded-2xl border transition-all bg-white/5 border-white/5 group/card hover:border-primary/30">
                    <p className="mb-2 font-black tracking-widest uppercase text-[10px] text-slate-500">
                      Health Score
                    </p>
                    <p className="text-5xl font-black text-white transition-colors group-hover/card:text-primary">
                      {health.score}
                      <span className="ml-1 text-xl opacity-50 text-slate-500">
                        /100
                      </span>
                    </p>
                  </div>

                  <div className="flex flex-col justify-center p-6 text-center rounded-2xl border transition-all bg-white/5 border-white/5 group/card hover:border-emerald-500/30">
                    <p className="mb-2 font-black tracking-widest uppercase text-[10px] text-slate-500">
                      Savings Rate
                    </p>
                    <p className="text-4xl font-black text-white transition-colors group-hover/card:text-emerald-400">
                      {isNaN(health.savings_rate)
                        ? "0.0%"
                        : `${(health.savings_rate * 100).toFixed(1)}%`}
                    </p>
                  </div>

                  <div className="flex flex-col justify-center p-6 text-center rounded-2xl border transition-all bg-white/5 border-white/5 group/card hover:border-violet-500/30">
                    <p className="mb-2 font-black tracking-widest uppercase text-[10px] text-slate-500">
                      Budget Adherence
                    </p>
                    <p className="text-4xl font-black text-white transition-colors group-hover/card:text-violet-400">
                      {typeof health.budget_adherence === "string"
                        ? health.budget_adherence === "good"
                          ? "100%"
                          : "0.0%"
                        : isNaN(health.budget_adherence)
                          ? "0.0%"
                          : `${(health.budget_adherence * 100).toFixed(1)}%`}
                    </p>
                  </div>

                  <div className="flex flex-col justify-center p-6 text-center rounded-2xl border transition-all bg-white/5 border-white/5 group/card hover:border-amber-500/30">
                    <p className="mb-2 font-black tracking-widest uppercase text-[10px] text-slate-500">
                      Goal Progress
                    </p>
                    <p className="text-4xl font-black text-white transition-colors group-hover/card:text-amber-400">
                      {isNaN(health.goal_progress)
                        ? "0.0%"
                        : `${(health.goal_progress * 100).toFixed(1)}%`}
                    </p>
                  </div>
                </div>

                <div className="p-6 mt-8 rounded-2xl border bg-primary/5 border-primary/20">
                  <div className="flex gap-4 items-start">
                    <ShieldCheck className="w-6 h-6 text-primary shrink-0" />
                    <div>
                      <p className="mb-1 text-sm font-bold text-primary">
                        Financial Stability Note
                      </p>
                      <p className="text-xs italic leading-relaxed text-slate-400">
                        Your financial health score is based on spending
                        patterns, savings, and budget adherence. Consistently
                        staying within budget will increase your score over
                        time.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
