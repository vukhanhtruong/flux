import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Landmark, TrendingUp, ArrowUpRight, ArrowDownRight, PieChart as PieIcon } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Asset } from "../types";
import {
  type PerformanceRange,
  type PortfolioSnapshot,
  computePerformance,
  computePortfolioTotal,
  filterSnapshotsForRange,
  loadSnapshots,
  recordSnapshot,
} from "../lib/assetsPerformance";

const ALLOCATION_COLORS = ["#38BDF8", "#10B981", "#F59E0B", "#EF4444", "#A78BFA", "#14B8A6"];

export function Assets() {
  const { profile } = useProfile();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<PerformanceRange>("30d");

  useEffect(() => {
    async function fetchAssets() {
      setLoading(true);
      setError(null);
      try {
        const response = await api.listAssets(USER_ID);
        setAssets(response);

        const total = computePortfolioTotal(response);
        const updated = recordSnapshot(total);
        setSnapshots(updated);
      } catch (err) {
        console.error("Failed to fetch assets:", err);
        setError("Failed to load latest assets. Showing last tracked performance history.");
        setSnapshots(loadSnapshots());
      } finally {
        setLoading(false);
      }
    }

    fetchAssets();
  }, []);

  const totalValue = useMemo(() => computePortfolioTotal(assets), [assets]);

  const daily = useMemo(() => computePerformance(snapshots, { now: Date.now(), range: "24h" }), [snapshots]);
  const weekly = useMemo(() => computePerformance(snapshots, { now: Date.now(), range: "7d" }), [snapshots]);
  const monthly = useMemo(() => computePerformance(snapshots, { now: Date.now(), range: "30d" }), [snapshots]);

  const chartData = useMemo(() => {
    const points = filterSnapshotsForRange(snapshots, { now: Date.now(), range });
    return points.map((point) => ({
      time: new Date(point.timestamp).toLocaleDateString(profile.locale, {
        month: "short",
        day: "numeric",
        timeZone: profile.timezone,
      }),
      fullDate: point.timestamp,
      value: point.totalValue,
    }));
  }, [snapshots, range, profile.locale]);

  const allocationData = useMemo(() => {
    const totals = assets.reduce<Record<string, number>>((acc, asset) => {
      const type = asset.asset_type || "unknown";
      const raw = asset.value ?? asset.amount ?? "0";
      const value = Number(raw);
      if (!Number.isFinite(value)) return acc;
      acc[type] = (acc[type] || 0) + value;
      return acc;
    }, {});

    return Object.entries(totals)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [assets]);

  if (loading) {
    return <div className="text-slate-400">Loading assets...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Assets</h1>
        <p className="text-slate-400">Read-only portfolio and performance tracking.</p>
      </div>

      {error && (
        <div className="glass-card border-l-4 border-l-red-500 p-5 text-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Portfolio Value" value={formatCurrency(totalValue, profile.currency, profile.locale)} icon={Landmark} />
        <ChangeMetricCard title="24h Change" metric={daily} currency={profile.currency} locale={profile.locale} />
        <ChangeMetricCard title="7d Change" metric={weekly} currency={profile.currency} locale={profile.locale} />
        <ChangeMetricCard title="30d Change" metric={monthly} currency={profile.currency} locale={profile.locale} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:gap-6 lg:gap-8 xl:grid-cols-3">
        <div className="glass-card p-4 md:p-6 xl:col-span-2">
          <div className="mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sm:gap-0">
            <h2 className="text-xl font-bold text-white">Portfolio Performance</h2>
            <select
              value={range}
              onChange={(e) => setRange(e.target.value as PerformanceRange)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-slate-300 outline-none focus:border-primary/50"
            >
              <option value="7d" className="bg-dark">Last 7d</option>
              <option value="30d" className="bg-dark">Last 30d</option>
              <option value="90d" className="bg-dark">Last 90d</option>
              <option value="1y" className="bg-dark">Last 1y</option>
              <option value="all" className="bg-dark">All</option>
            </select>
          </div>
          {chartData.length < 2 ? (
            <div className="h-[300px] flex items-center justify-center text-slate-500 italic">
              Collecting performance history...
            </div>
          ) : (
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="assetPerf" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748B" tickLine={false} axisLine={false} />
                  <YAxis
                    stroke="#64748B"
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => formatCurrency(value, profile.currency, profile.locale)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1E293B",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "12px",
                    }}
                    formatter={(value) => formatCurrency(Number(value), profile.currency, profile.locale)}
                    labelFormatter={(label, payload) => {
                      const raw = payload?.[0]?.payload?.fullDate;
                      if (!raw) return label;
                      return new Date(raw).toLocaleDateString(profile.locale, { timeZone: profile.timezone });
                    }}
                  />
                  <Area type="monotone" dataKey="value" stroke="#F59E0B" strokeWidth={3} fill="url(#assetPerf)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="glass-card p-4 md:p-6">
          <div className="mb-4 flex items-center gap-2">
            <PieIcon className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-white">Allocation</h2>
          </div>
          {allocationData.length === 0 ? (
            <div className="h-[300px] flex items-center justify-center text-slate-500 italic">
              No assets tracked yet.
            </div>
          ) : (
            <>
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={allocationData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                      {allocationData.map((_, idx) => (
                        <Cell key={idx} fill={ALLOCATION_COLORS[idx % ALLOCATION_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => formatCurrency(Number(value), profile.currency, profile.locale)}
                      contentStyle={{
                        backgroundColor: "#1E293B",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2">
                {allocationData.map((item, idx) => (
                  <div key={item.name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 text-slate-300">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: ALLOCATION_COLORS[idx % ALLOCATION_COLORS.length] }}
                      />
                      <span className="capitalize">{item.name}</span>
                    </div>
                    <span className="font-medium text-white">
                      {formatCurrency(item.value, profile.currency, profile.locale)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="border-b border-white/5 px-4 md:px-6 py-4 md:py-5 bg-white/[0.02]">
          <h2 className="text-xl font-bold text-white">Assets List</h2>
        </div>
        {assets.length === 0 ? (
          <div className="px-4 md:px-6 py-10 md:py-14 text-center text-slate-500 italic">No assets tracked yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-4 md:px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Name</th>
                  <th className="px-4 md:px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Type</th>
                  <th className="px-4 md:px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Category</th>
                  <th className="px-4 md:px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Interest</th>
                  <th className="px-4 md:px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Next Date</th>
                  <th className="px-4 md:px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400 text-right">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {[...assets]
                  .sort((a, b) => Number(b.value ?? b.amount ?? 0) - Number(a.value ?? a.amount ?? 0))
                  .map((asset) => {
                    const value = Number(asset.value ?? asset.amount ?? 0);
                    const interest = Number(asset.interest_rate ?? 0);
                    return (
                      <tr key={asset.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-4 md:px-6 py-3 md:py-4 text-white font-medium whitespace-nowrap">{asset.name}</td>
                        <td className="px-4 md:px-6 py-3 md:py-4 text-slate-300 capitalize whitespace-nowrap">{asset.asset_type || "-"}</td>
                        <td className="px-4 md:px-6 py-3 md:py-4 text-slate-300 whitespace-nowrap">{asset.category || "-"}</td>
                        <td className="px-4 md:px-6 py-3 md:py-4 text-slate-300 whitespace-nowrap">{Number.isFinite(interest) ? `${interest}%` : "-"}</td>
                        <td className="px-4 md:px-6 py-3 md:py-4 text-slate-300 whitespace-nowrap">
                          {asset.next_date
                            ? formatDate(asset.next_date, profile.locale, profile.timezone)
                            : "-"}
                        </td>
                        <td className="px-4 md:px-6 py-3 md:py-4 text-right text-white font-semibold whitespace-nowrap">
                          {formatCurrency(Number.isFinite(value) ? value : 0, profile.currency, profile.locale)}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon: Icon }: { title: string; value: string; icon: typeof Landmark }) {
  return (
    <div className="glass-card p-4 md:p-6 border-l-4 border-l-transparent hover:border-l-primary transition-all">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
        <div className="rounded-lg bg-primary/10 p-2 text-primary">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function ChangeMetricCard({
  title,
  metric,
  currency,
  locale,
}: {
  title: string;
  metric: ReturnType<typeof computePerformance>;
  currency: string;
  locale: string;
}) {
  if (!metric) {
    return <MetricCard title={title} value="Collecting data" icon={TrendingUp} />;
  }

  const positive = metric.delta >= 0;
  const pct = metric.deltaPct == null ? "-" : `${(metric.deltaPct * 100).toFixed(2)}%`;

  return (
    <div className="glass-card p-4 md:p-6 border-l-4 border-l-transparent hover:border-l-primary transition-all">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
        <div className={`rounded-lg p-2 ${positive ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
          {positive ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
        </div>
      </div>
      <p className={`text-2xl font-bold ${positive ? "text-emerald-300" : "text-red-300"}`}>
        {formatCurrency(metric.delta, currency, locale)}
      </p>
      <p className="mt-1 text-xs font-medium text-slate-400">{pct}</p>
    </div>
  );
}
