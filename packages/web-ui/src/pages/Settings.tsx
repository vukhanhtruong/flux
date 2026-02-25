import { useEffect, useState } from "react";
import { User, Send, Smartphone, Cpu, Database, Save, Globe, Clock, Coins } from "lucide-react";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";

type Tab = "general" | "messaging" | "system";

export function Settings() {
  const { profile, loading, error, saveProfile } = useProfile();
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    currency: profile.currency,
    timezone: profile.timezone,
    locale: profile.locale,
  });

  useEffect(() => {
    setFormData({
      currency: profile.currency,
      timezone: profile.timezone,
      locale: profile.locale,
    });
  }, [profile.currency, profile.timezone, profile.locale]);

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

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaveStatus(null);
    setSaving(true);
    try {
      await saveProfile({
        currency: formData.currency.trim(),
        timezone: formData.timezone.trim(),
        locale: formData.locale,
      });
      setSaveStatus("Saved");
    } catch {
      setSaveStatus("Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "general", label: "General" },
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
          <form onSubmit={handleSave} className="space-y-8">
            <div className="glass-card p-10 space-y-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <User className="w-5 h-5 text-primary" />
                  <h2 className="text-xl font-bold text-white tracking-tight">Account Information</h2>
                </div>
                {saveStatus && (
                  <p
                    className={`text-xs font-bold uppercase tracking-widest ${saveStatus === "Saved" ? "text-emerald-400" : "text-red-400"
                      }`}
                  >
                    {saveStatus}
                  </p>
                )}
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
                      onChange={(e) =>
                        setFormData({ ...formData, currency: e.target.value.toUpperCase() })
                      }
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12"
                      placeholder="e.g. USD, VND, EUR"
                      required
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
                      onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12"
                      placeholder="Asia/Ho_Chi_Minh"
                      required
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
                      onChange={(e) => setFormData({ ...formData, locale: e.target.value })}
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12 appearance-none"
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

              <div className="pt-6 border-t border-white/5 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary min-w-[160px] flex items-center justify-center gap-2"
                >
                  <Save size={18} />
                  {saving ? "Deploying Changes..." : "Apply Settings"}
                </button>
              </div>
            </div>
          </form>
        )}

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

            <div className="glass-card p-8 group">
              <div className="flex items-center gap-4 mb-6">
                <div className="p-3 bg-[#25D366]/10 rounded-xl group-hover:scale-110 transition-transform">
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
      </div>
    </div>
  );
}
