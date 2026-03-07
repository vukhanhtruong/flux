import { useState, useEffect } from "react";
import { User, Send, Smartphone, Cpu, Database, Globe, Clock, Coins, CalendarClock } from "lucide-react";
import { DataTab } from "./settings/DataTab";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { ScheduledTask } from "../types";

type Tab = "general" | "data" | "messaging" | "system" | "scheduled-tasks";

function formatScheduleValue(type: string, value: string): string {
  if (type === "interval") {
    const ms = parseInt(value, 10);
    if (ms >= 86400000) return `${Math.round(ms / 86400000)}d`;
    if (ms >= 3600000) return `${Math.round(ms / 3600000)}h`;
    if (ms >= 60000) return `${Math.round(ms / 60000)}m`;
    return `${Math.round(ms / 1000)}s`;
  }
  return value;
}

export function Settings() {
  const { profile, loading, error } = useProfile();
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const [healthStatus, setHealthStatus] = useState<string | null>(null);

  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [tasksError, setTasksError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab !== "scheduled-tasks") return;
    setTasksLoading(true);
    setTasksError(null);
    api
      .listScheduledTasks(USER_ID)
      .then(setTasks)
      .catch((err) => setTasksError(String(err)))
      .finally(() => setTasksLoading(false));
  }, [activeTab]);

  const formData = {
    currency: profile.currency,
    timezone: profile.timezone,
    locale: profile.locale,
  };

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  async function checkHealth() {
    try {
      const res = await fetch(`${apiBaseUrl}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthStatus(`Healthy - ${JSON.stringify(data)}`);
      } else {
        setHealthStatus(`Unhealthy - ${res.status} ${res.statusText}`);
      }
    } catch (err) {
      setHealthStatus(`Unreachable - ${err}`);
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "general", label: "General" },
    { key: "data", label: "Data" },
    { key: "scheduled-tasks", label: "Scheduled Tasks" },
    { key: "messaging", label: "Messaging Platforms" },
    { key: "system", label: "System" },
  ];

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Settings</h1>
          <p className="text-slate-400">Manage your Account, Notifications, and System preferences.</p>
        </div>
      </div>

      <div className="flex gap-2 p-1 bg-white/5 rounded-xl w-fit border border-white/5">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-6 py-2 text-sm font-bold transition-all ${activeTab === tab.key
              ? "bg-primary text-dark"
              : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        {activeTab === "general" && (
          <div className="space-y-8">
            <div className="glass-card p-10 space-y-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <User className="w-5 h-5 text-primary" />
                  <h2 className="text-xl font-bold text-white tracking-tight">Account Information</h2>
                </div>
              </div>

              {loading && <p className="text-sm text-slate-500 italic">Loading profile...</p>}
              {error && <p className="text-sm text-red-400">{error}</p>}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                <div className="space-y-2">
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                    User Identification
                  </label>
                  <div className="group relative">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
                    <p className="relative w-full bg-dark border border-white/10 rounded-xl px-4 py-3 text-slate-300 font-mono text-sm leading-none flex items-center h-12">
                      {USER_ID}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Preferred Currency
                  </label>
                  <div className="relative">
                    <Coins className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      value={formData.currency}
                      readOnly
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12 opacity-70 cursor-not-allowed"
                      placeholder="e.g. USD, VND, EUR"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Timezone
                  </label>
                  <div className="relative">
                    <Clock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      value={formData.timezone}
                      readOnly
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12 opacity-70 cursor-not-allowed"
                      placeholder="Asia/Ho_Chi_Minh"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Locale / Language
                  </label>
                  <div className="relative">
                    <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <select
                      value={formData.locale}
                      disabled
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12 appearance-none opacity-70 cursor-not-allowed"
                    >
                      <option value="vi-VN" className="bg-dark">
                        Vietnamese (vi-VN)
                      </option>
                      <option value="en-US" className="bg-dark">
                        English (en-US)
                      </option>
                    </select>
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}

        {activeTab === "data" && <DataTab />}

        {activeTab === "messaging" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="glass-card p-8 group">
              <div className="flex items-center gap-4 mb-6">
                <div className="p-3 bg-[#0088cc]/10 rounded-xl group-hover:scale-110 transition-transform">
                  <Send className="w-6 h-6 text-[#0088cc]" />
                </div>
                <h3 className="text-xl font-bold text-white">Telegram Bridge</h3>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed mb-8">
                Connect your Flux Assistant to Telegram for high-speed, messaging-based finance
                management.
              </p>

              <div className="space-y-4">
                <div className="p-6 bg-white/5 rounded-2xl border border-white/5">
                  <p className="text-[10px] font-black uppercase tracking-widest text-primary mb-4">
                    Configuration Steps
                  </p>
                  <ol className="list-none space-y-4">
                    {[
                      { step: "1", text: "New bot via @BotFather" },
                      { step: "2", text: "Secure your API token" },
                      { step: "3", text: "Configure environment variables" },
                      { step: "4", text: "Restart AI agent-bot container" },
                    ].map((item) => (
                      <li key={item.step} className="flex gap-4 items-center">
                        <span className="flex-none w-6 h-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-[10px] font-bold text-slate-400">
                          {item.step}
                        </span>
                        <span className="text-sm text-slate-300">{item.text}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>

            <div className="glass-card p-8 group relative overflow-hidden opacity-60 grayscale-[50%]">
              <div className="absolute top-4 right-4 px-2.5 py-1 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded text-[10px] font-bold uppercase tracking-widest backdrop-blur-sm shadow-[0_0_15px_rgba(245,158,11,0.2)]">
                Coming Soon
              </div>
              <div className="flex items-center gap-4 mb-6">
                <div className="p-3 bg-[#25D366]/10 rounded-xl">
                  <Smartphone className="w-6 h-6 text-[#25D366]" />
                </div>
                <h3 className="text-xl font-bold text-white">WhatsApp Integration</h3>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed mb-8">
                Interact with your balance and transactions directly through WhatsApp using our
                secure bridge.
              </p>

              <div className="space-y-4">
                <div className="p-6 bg-white/5 rounded-2xl border border-white/5">
                  <p className="text-[10px] font-black uppercase tracking-widest text-[#25D366] mb-4">
                    Deployment Guide
                  </p>
                  <ol className="list-none space-y-4">
                    {[
                      { step: "1", text: "Initalize WhatsApp docker profile" },
                      { step: "2", text: "Execute bridge login command" },
                      { step: "3", text: "Authorize via device QR scan" },
                    ].map((item) => (
                      <li key={item.step} className="flex gap-4 items-center">
                        <span className="flex-none w-6 h-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-[10px] font-bold text-slate-400">
                          {item.step}
                        </span>
                        <span className="text-sm text-slate-300">{item.text}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "system" && (
          <div className="glass-card p-10 space-y-10">
            <div className="flex items-center gap-3 mb-2">
              <Cpu className="w-5 h-5 text-secondary" />
              <h2 className="text-xl font-bold text-white tracking-tight">System Core</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">
                  Version
                </label>
                <div className="inline-flex items-center px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-bold text-white">
                  v0.1.0-alpha
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">
                  API Connectivity
                </label>
                <div className="flex items-center gap-4">
                  <button onClick={checkHealth} className="btn-secondary py-1.5 px-4 text-xs h-9">
                    Ping Server
                  </button>
                  {healthStatus && (
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full animate-pulse ${healthStatus.startsWith("Healthy")
                          ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"
                          : "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]"
                          }`}
                      />
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider ${healthStatus.startsWith("Healthy") ? "text-emerald-400" : "text-red-400"
                          }`}
                      >
                        {healthStatus.startsWith("Healthy") ? "Operational" : "Degraded"}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">
                  Storage Engine
                </label>
                <div className="flex items-center gap-2 text-slate-300">
                  <Database className="w-4 h-4 text-slate-500" />
                  <span className="text-xs font-bold">PostgreSQL Cluster</span>
                </div>
              </div>
            </div>

            <div className="p-6 bg-dark/50 border border-white/5 rounded-2xl">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 text-center">
                Infrastructure Connection String
              </label>
              <p className="text-center font-mono text-xs text-slate-600 truncate py-2">
                postgresql://***:***@postgres:5432/fluxfinance
              </p>
            </div>
          </div>
        )}

        {activeTab === "scheduled-tasks" && (
          <div className="glass-card p-10 space-y-8">
            <div className="flex items-center gap-3 mb-2">
              <CalendarClock className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-bold text-white tracking-tight">Active Scheduled Tasks</h2>
            </div>

            {tasksLoading && <p className="text-sm text-slate-500 italic">Loading tasks...</p>}
            {tasksError && <p className="text-sm text-red-400">{tasksError}</p>}

            {!tasksLoading && !tasksError && tasks.length === 0 && (
              <div className="text-center py-16">
                <CalendarClock className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-500 text-sm">No active scheduled tasks.</p>
              </div>
            )}

            {!tasksLoading && tasks.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Prompt</th>
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Type</th>
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Schedule</th>
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Status</th>
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Next Run</th>
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Last Run</th>
                      <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3">Linked Entity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task) => (
                      <tr key={task.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                        <td className="py-3 pr-4 text-slate-300 max-w-[200px] truncate" title={task.prompt}>{task.prompt}</td>
                        <td className="py-3 pr-4">
                          <span className="inline-flex items-center px-2 py-0.5 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-slate-400 uppercase">
                            {task.schedule_type}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-slate-400 font-mono text-xs">{formatScheduleValue(task.schedule_type, task.schedule_value)}</td>
                        <td className="py-3 pr-4">
                          <span className="inline-flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">{task.status}</span>
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-slate-400 text-xs">{formatDateTime(task.next_run_at, profile.locale, profile.timezone)}</td>
                        <td className="py-3 pr-4 text-slate-400 text-xs">{task.last_run_at ? formatDateTime(task.last_run_at, profile.locale, profile.timezone) : "—"}</td>
                        <td className="py-3 text-slate-400 text-xs">
                          {task.subscription_id ? `Subscription` : task.asset_id ? `Savings` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
