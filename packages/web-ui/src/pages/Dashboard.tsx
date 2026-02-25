import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { Transaction, FinancialHealth } from "../types";
import {
  TrendingUp,
  Wallet,
  Target,
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Search
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const mockChartData = [
  { name: "Mon", value: 4000 },
  { name: "Tue", value: 3000 },
  { name: "Wed", value: 2000 },
  { name: "Thu", value: 2780 },
  { name: "Fri", value: 1890 },
  { name: "Sat", value: 2390 },
  { name: "Sun", value: 3490 },
];

export function Dashboard() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [health, setHealth] = useState<FinancialHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [txns, healthData] = await Promise.all([
          api.listTransactions(USER_ID, 5),
          api.getFinancialHealth(
            USER_ID,
            new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
            new Date().toISOString().split("T")[0]
          ),
        ]);
        setTransactions(txns);
        setHealth(healthData);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
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
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Welcome back, User</h1>
          <p className="text-slate-400">
            Your finances are looking <span className="text-primary font-medium">solid</span> this month.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2.5 rounded-xl glass-card text-slate-400 hover:text-white transition-colors">
            <Search className="w-5 h-5" />
          </button>
          <button className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Add Transaction
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
            value={`${(health.budget_adherence * 100).toFixed(1)}%`}
            icon={Wallet}
            color="text-violet-400"
            bgColor="bg-violet-400/10"
          />
          <HealthCard
            title="Goal Progress"
            value={`${(health.goal_progress * 100).toFixed(1)}%`}
            icon={Target}
            color="text-sky-400"
            bgColor="bg-sky-400/10"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 glass-card p-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white">Financial Overview</h2>
            <select className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-slate-300 outline-none focus:border-primary/50 transition-colors">
              <option>Last 7 days</option>
              <option>Last 30 days</option>
            </select>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockChartData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
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
                  tickFormatter={(value) => `$${value}`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "12px",
                    color: "#F8FAFC"
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#F59E0B"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorValue)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card">
          <div className="p-6 border-b border-white/5 flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Recent Activity</h2>
            <button className="text-xs font-semibold text-primary hover:text-primary-light transition-colors">See all</button>
          </div>
          <div className="p-2">
            {transactions.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-slate-500 italic">No recent transactions</p>
              </div>
            ) : (
              <div className="space-y-1">
                {transactions.map((txn) => (
                  <div key={txn.id} className="flex items-center justify-between p-4 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group">
                    <div className="flex items-center gap-4">
                      <div className={`p-2.5 rounded-xl ${txn.type === "income" ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"}`}>
                        {txn.type === "income" ? <ArrowDownRight className="w-5 h-5" /> : <ArrowUpRight className="w-5 h-5" />}
                      </div>
                      <div>
                        <p className="font-semibold text-white group-hover:text-primary transition-colors">{txn.description}</p>
                        <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                          {txn.category} • {new Date(txn.date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className={`text-lg font-bold ${txn.type === "income" ? "text-emerald-400" : "text-slate-200"}`}>
                      {txn.type === "income" ? "+" : "-"}${txn.amount}
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

function HealthCard({ title, value, icon: Icon, color, bgColor }: any) {
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
}
