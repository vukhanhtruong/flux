import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Search,
  ShieldCheck,
  TrendingUp,
  Landmark,
  Wallet,
  Target,
  ArrowDownRight,
  ArrowUpRight,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import {
  computePerformance,
  computePortfolioTotal,
  filterSnapshotsForRange,
  recordSnapshot,
  type PortfolioSnapshot,
} from "../lib/assetsPerformance";
import type { Transaction, FinancialHealth, Asset } from "../types";

export function Dashboard() {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [health, setHealth] = useState<FinancialHealth | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetSnapshots, setAssetSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<"7d" | "30d">("7d");
  const [chartData, setChartData] = useState<{ name: string; expense: number; income: number; fullDate: string }[]>([]);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchData() {
      setLoading(true);
      try {
        const days = timeRange === "7d" ? 7 : 30;
        const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
          .toISOString()
          .split("T")[0];
        const endDate = new Date().toISOString().split("T")[0];

        // We wrap fetching but abort won't natively cancel fetch inside api wrapper unless
        // we pass signal, but it will prevent state setting on unmount.
        const [allTxns, healthData, assetsData] = await Promise.all([
          api.listTransactions(USER_ID, 5),
          api.getFinancialHealth(USER_ID, startDate, endDate),
          api.listAssets(USER_ID),
        ]);

        if (abortController.signal.aborted) return;

        setTransactions(allTxns);
        setHealth(healthData);
        setAssets(assetsData);
        setAssetSnapshots(recordSnapshot(computePortfolioTotal(assetsData)));

        const dataMap: Record<string, { expense: number; income: number }> = {};
        for (let i = days - 1; i >= 0; i--) {
          const d = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
          const dateStr = d.toISOString().split("T")[0];
          dataMap[dateStr] = { expense: 0, income: 0 };
        }

        allTxns.forEach((txn) => {
          const dateStr = txn.date.split("T")[0];
          if (Object.prototype.hasOwnProperty.call(dataMap, dateStr)) {
            if (txn.type === "expense") {
              dataMap[dateStr].expense += parseFloat(txn.amount);
            } else if (txn.type === "income") {
              dataMap[dateStr].income += parseFloat(txn.amount);
            }
          }
        });

        const formattedData = Object.entries(dataMap)
          .map(([date, values]) => ({
            name: new Date(date + "T00:00:00Z").toLocaleDateString(profile.locale, { weekday: "short", timeZone: profile.timezone }),
            expense: parseFloat(values.expense.toFixed(2)),
            income: parseFloat(values.income.toFixed(2)),
            fullDate: date,
          }))
          .sort((a, b) => a.fullDate.localeCompare(b.fullDate));

        if (abortController.signal.aborted) return;
        setChartData(formattedData);
      } catch (error) {
        if (!abortController.signal.aborted) {
          console.error("Failed to fetch dashboard data:", error);
        }
      } finally {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
      }
    }
    fetchData();

    return () => {
      abortController.abort();
    };
  }, [timeRange, profile.locale, profile.timezone]);

  const handleTimeRangeChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value as "7d" | "30d");
  }, []);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 bg-white/10 rounded-full"></div>
          <div className="h-4 w-32 bg-white/10 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Welcome back</h1>
          <p className="text-slate-400">
            Your finances are looking <span className="text-primary font-medium">solid</span> this month.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/transactions")}
            className="p-2.5 rounded-xl glass-card text-slate-400 hover:text-white transition-colors"
            title="View Transactions"
          >
            <Search className="w-5 h-5" />
          </button>
        </div>
      </div>

      {health && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <HealthCard
            title="Health Score"
            value={`${health.score}/100`}
            icon={ShieldCheck}
            color="text-emerald-400"
            bgColor="bg-emerald-400/10"
          />
          <HealthCard
            title="Savings Rate"
            value={`${(health.savings_rate * 100).toFixed(1)}%`}
            icon={TrendingUp}
            color="text-primary"
            bgColor="bg-primary/10"
          />
          <HealthCard
            title="Budget Adherence"
            value={typeof health.budget_adherence === 'string'
              ? (health.budget_adherence === 'good' ? "100%" : "0.0%")
              : (isNaN(health.budget_adherence) ? "0.0%" : `${(health.budget_adherence * 100).toFixed(1)}%`)}
            icon={Wallet}
            color="text-violet-400"
            bgColor="bg-violet-400/10"
          />
          <HealthCard
            title="Goal Progress"
            value={isNaN(health.goal_progress) ? "0.0%" : `${(health.goal_progress * 100).toFixed(1)}%`}
            icon={Target}
            color="text-sky-400"
            bgColor="bg-sky-400/10"
          />
        </div>
      )}

      <AssetOverviewCard assets={assets} snapshots={assetSnapshots} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 lg:gap-8">
        <div className="lg:col-span-2 glass-card p-4 md:p-6 lg:p-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 md:mb-8 gap-4 sm:gap-0">
            <h2 className="text-xl font-bold text-white">Financial Overview</h2>
            <select
              value={timeRange}
              onChange={handleTimeRangeChange}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-slate-300 outline-none focus:border-primary/50 transition-colors cursor-pointer"
            >
              <option value="7d" className="bg-dark">
                Last 7 days
              </option>
              <option value="30d" className="bg-dark">
                Last 30 days
              </option>
            </select>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="#475569"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  dy={10}
                />
                <YAxis
                  stroke="#475569"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => formatCurrency(Number(value), profile.currency, profile.locale)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "12px",
                    color: "#F8FAFC",
                  }}
                  formatter={(value, name) => [
                    formatCurrency(Number(value), profile.currency, profile.locale),
                    name === "expense" ? "Expenses" : "Income"
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="income"
                  stroke="#10B981"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorIncome)"
                  animationDuration={1500}
                />
                <Area
                  type="monotone"
                  dataKey="expense"
                  stroke="#F59E0B"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorExpense)"
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card">
          <div className="p-6 border-b border-white/5 flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Recent Activity</h2>
            <button
              onClick={() => navigate("/transactions")}
              className="text-xs font-semibold text-primary hover:text-primary-light transition-colors"
            >
              See all
            </button>
          </div>
          <div className="p-2">
            {transactions.length === 0 ? (
              <div className="p-6 md:p-8 text-center">
                <p className="text-slate-500 italic">No recent transactions</p>
              </div>
            ) : (
              <div className="space-y-1">
                {transactions.map((txn) => (
                  <div
                    key={txn.id}
                    className="flex items-center justify-between p-4 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className={`p-2.5 rounded-xl ${txn.type === "income"
                          ? "bg-emerald-400/10 text-emerald-400"
                          : "bg-red-400/10 text-red-400"
                          }`}
                      >
                        {txn.type === "income" ? (
                          <ArrowDownRight className="w-5 h-5" />
                        ) : (
                          <ArrowUpRight className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <p className="font-semibold text-white group-hover:text-primary transition-colors">
                          {txn.description}
                        </p>
                        <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                          {txn.category} • {formatDate(txn.date, profile.locale, profile.timezone)}
                        </p>
                      </div>
                    </div>
                    <div
                      className={`text-lg font-bold ${txn.type === "income" ? "text-emerald-400" : "text-slate-200"
                        }`}
                    >
                      {txn.type === "income" ? "+" : "-"}
                      {formatCurrency(txn.amount, profile.currency, profile.locale)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const AssetOverviewCard = React.memo(function AssetOverviewCard({
  assets,
  snapshots,
}: {
  assets: Asset[];
  snapshots: PortfolioSnapshot[];
}) {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const totalValue = computePortfolioTotal(assets);
  const weekly = computePerformance(snapshots, { now: Date.now(), range: "7d" });
  const sparkline = filterSnapshotsForRange(snapshots, { now: Date.now(), range: "30d" }).map((point) => ({
    value: point.totalValue,
    name: new Date(point.timestamp).toLocaleDateString(profile.locale, {
      month: "short",
      day: "numeric",
      timeZone: profile.timezone,
    }),
  }));

  const topAssets = useMemo(() => {
    return [...assets]
      .sort((a, b) => Number(b.value ?? b.amount ?? 0) - Number(a.value ?? a.amount ?? 0))
      .slice(0, 3);
  }, [assets]);

  return (
    <div className="glass-card p-4 md:p-6 lg:p-8">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Assets Overview</h2>
          <p className="text-slate-400 text-sm">Read-only portfolio snapshot and 7-day momentum.</p>
        </div>
        <button
          onClick={() => navigate("/assets")}
          className="btn-primary text-sm px-4 py-2"
        >
          View all assets
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass-card p-5 border-white/5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Portfolio Value</h3>
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <Landmark className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white">
            {formatCurrency(totalValue, profile.currency, profile.locale)}
          </p>
          <p className="mt-2 text-xs text-slate-400">
            {weekly
              ? `${weekly.delta >= 0 ? "+" : ""}${formatCurrency(weekly.delta, profile.currency, profile.locale)} in 7d`
              : "Collecting 7d history"}
          </p>
        </div>

        <div className="glass-card p-5 border-white/5 lg:col-span-2">
          {sparkline.length < 2 ? (
            <div className="h-[130px] flex items-center justify-center text-slate-500 italic">
              Collecting performance history...
            </div>
          ) : (
            <div className="h-[130px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sparkline}>
                  <defs>
                    <linearGradient id="assetSparkline" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    fill="url(#assetSparkline)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            {topAssets.length === 0 ? (
              <p className="text-slate-500 italic text-sm">No assets tracked yet.</p>
            ) : (
              topAssets.map((asset) => (
                <div key={asset.id} className="rounded-lg bg-white/5 p-3">
                  <p className="text-xs uppercase tracking-wider text-slate-400">{asset.name}</p>
                  <p className="text-sm font-semibold text-white">
                    {formatCurrency(
                      Number(asset.value ?? asset.amount ?? 0),
                      profile.currency,
                      profile.locale,
                    )}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
  }
);

const HealthCard = React.memo(function HealthCard({ title, value, icon: Icon, color, bgColor }: any) {
  return (
    <div className="glass-card p-6 border-l-4 border-l-transparent hover:border-l-primary transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">{title}</h3>
        <div className={`p-2 rounded-lg ${bgColor} ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-3xl font-bold text-white tracking-tight">{value}</p>
    </div>
  );
});
