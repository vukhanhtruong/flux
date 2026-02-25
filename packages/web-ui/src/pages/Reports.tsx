import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { TrendingUp, ArrowUpRight, ArrowDownRight, ShieldCheck, Target } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { SpendingReport, FinancialHealth } from "../types";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6"];

export function Reports() {
  const [report, setReport] = useState<SpendingReport | null>(null);
  const [health, setHealth] = useState<FinancialHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const today = new Date().toISOString().split("T")[0];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
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
      setError("Failed to load reports. Make sure you have transactions in this date range.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchReports();
  }, [startDate, endDate]);

  const pieData = report
    ? Object.entries(report.category_breakdown).map(([name, value]) => ({
      name,
      value: parseFloat(value),
    }))
    : [];

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Reports</h1>
          <p className="text-slate-400">Deep dive into your spending patterns and financial health.</p>
        </div>

        <div className="flex items-center gap-4 glass-card p-2 px-4 border-white/5">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">From</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-transparent text-white text-xs outline-none focus:text-primary transition-colors cursor-pointer"
            />
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">To</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-transparent text-white text-xs outline-none focus:text-primary transition-colors cursor-pointer"
            />
          </div>
        </div>
      </div>

      {loading && (
        <div className="glass-card p-20 text-center animate-pulse">
          <p className="text-slate-500 text-lg">Analyzing your finances...</p>
        </div>
      )}

      {error && (
        <div className="glass-card p-8 border-l-4 border-l-red-500 flex items-center gap-4">
          <div className="p-3 bg-red-500/10 rounded-xl">
            <TrendingUp className="w-6 h-6 text-red-500 rotate-180" />
          </div>
          <p className="text-red-200">{error}</p>
        </div>
      )}

      {!loading && !error && report && (
        <>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="glass-card p-8 hover:border-emerald-500/30 transition-all group">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-emerald-500/10 rounded-lg">
                  <ArrowUpRight className="w-5 h-5 text-emerald-500" />
                </div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Total Income</h3>
              </div>
              <p className="text-4xl font-black text-white group-hover:text-emerald-400 transition-colors">
                ${parseFloat(report.total_income).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className="glass-card p-8 hover:border-red-500/30 transition-all group">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-red-500/10 rounded-lg">
                  <ArrowDownRight className="w-5 h-5 text-red-500" />
                </div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Total Expenses</h3>
              </div>
              <p className="text-4xl font-black text-white group-hover:text-red-400 transition-colors">
                ${parseFloat(report.total_expenses).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className={`glass-card p-8 hover:border-primary/30 transition-all group ${parseFloat(report.net_savings) >= 0 ? 'border-primary/10' : 'border-red-500/10'}`}>
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-2 rounded-lg ${parseFloat(report.net_savings) >= 0 ? 'bg-primary/10' : 'bg-red-500/10'}`}>
                  <ShieldCheck className={`w-5 h-5 ${parseFloat(report.net_savings) >= 0 ? 'text-primary' : 'text-red-500'}`} />
                </div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Net Savings</h3>
              </div>
              <p className={`text-4xl font-black transition-colors ${parseFloat(report.net_savings) >= 0 ? 'text-white group-hover:text-primary' : 'text-red-400'}`}>
                ${parseFloat(report.net_savings).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
            {pieData.length > 0 && (
              <div className="glass-card p-10">
                <div className="flex items-center gap-3 mb-8">
                  <div className="p-2 bg-violet-500/10 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-violet-500" />
                  </div>
                  <h2 className="text-xl font-bold text-white tracking-tight">Spending by Category</h2>
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
                      >
                        {pieData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="outline-none" />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff' }}
                        itemStyle={{ color: '#fff' }}
                        formatter={(value) => `$${Number(value).toFixed(2)}`}
                      />
                      <Legend
                        layout="vertical"
                        align="right"
                        verticalAlign="middle"
                        formatter={(value) => <span className="text-slate-300 text-sm">{value}</span>}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {health && (
              <div className="glass-card p-10 flex flex-col">
                <div className="flex items-center gap-3 mb-10">
                  <div className="p-2 bg-amber-500/10 rounded-lg">
                    <Target className="w-5 h-5 text-amber-500" />
                  </div>
                  <h2 className="text-xl font-bold text-white tracking-tight">Financial Health Insights</h2>
                </div>

                <div className="grid grid-cols-2 gap-8 flex-1">
                  <div className="p-6 bg-white/5 rounded-2xl border border-white/5 hover:border-primary/30 transition-all flex flex-col justify-center text-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Health Score</p>
                    <p className="text-5xl font-black text-white">{health.score}<span className="text-xl text-slate-500 opacity-50 ml-1">/100</span></p>
                  </div>

                  <div className="p-6 bg-white/5 rounded-2xl border border-white/5 hover:border-emerald-500/30 transition-all flex flex-col justify-center text-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Savings Rate</p>
                    <p className="text-4xl font-black text-white">{(health.savings_rate * 100).toFixed(1)}%</p>
                  </div>

                  <div className="p-6 bg-white/5 rounded-2xl border border-white/5 hover:border-violet-500/30 transition-all flex flex-col justify-center text-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Budget Adherence</p>
                    <p className="text-4xl font-black text-white">{(health.budget_adherence * 100).toFixed(1)}%</p>
                  </div>

                  <div className="p-6 bg-white/5 rounded-2xl border border-white/5 hover:border-amber-500/30 transition-all flex flex-col justify-center text-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Goal Progress</p>
                    <p className="text-4xl font-black text-white">{(health.goal_progress * 100).toFixed(1)}%</p>
                  </div>
                </div>

                <div className="mt-8 p-6 bg-primary/5 rounded-2xl border border-primary/20">
                  <div className="flex items-start gap-4">
                    <ShieldCheck className="w-6 h-6 text-primary shrink-0" />
                    <div>
                      <p className="text-sm font-bold text-primary mb-1">Financial Stability Note</p>
                      <p className="text-xs text-slate-400 leading-relaxed">Your financial health score is based on spending patterns, savings, and budget adherence. Consistently staying within budget will increase your score over time.</p>
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
