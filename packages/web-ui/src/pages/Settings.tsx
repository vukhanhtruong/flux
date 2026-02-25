import { useEffect, useState } from "react";
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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">Configure your preferences and account settings.</p>
      </div>

      <div className="flex gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              activeTab === tab.key
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100 shadow"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "general" && (
        <form onSubmit={handleSave} className="rounded-lg bg-white p-6 shadow space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">General</h2>

          {loading && <p className="text-sm text-gray-600">Loading profile...</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          <div>
            <label className="block text-sm font-medium text-gray-500">User ID</label>
            <p className="mt-1 rounded-md bg-gray-50 px-3 py-2 text-gray-900 font-mono text-sm">
              {USER_ID}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-500">Currency</label>
            <input
              type="text"
              value={formData.currency}
              onChange={(e) => setFormData({ ...formData, currency: e.target.value.toUpperCase() })}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="VND"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-500">Timezone</label>
            <input
              type="text"
              value={formData.timezone}
              onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="Asia/Ho_Chi_Minh"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-500">Language</label>
            <select
              value={formData.locale}
              onChange={(e) => setFormData({ ...formData, locale: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
            >
              <option value="vi-VN">Vietnamese (vi-VN)</option>
              <option value="en-US">English (en-US)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-500">API Base URL</label>
            <p className="mt-1 rounded-md bg-gray-50 px-3 py-2 text-gray-900 font-mono text-sm">
              {apiBaseUrl}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            {saveStatus && (
              <p className={`text-sm ${saveStatus === "Saved" ? "text-green-600" : "text-red-600"}`}>
                {saveStatus}
              </p>
            )}
          </div>
        </form>
      )}

      {activeTab === "messaging" && (
        <div className="space-y-4">
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-lg font-semibold text-gray-900">Telegram</h3>
            <p className="mt-2 text-sm text-gray-600">
              Connect your flux bot to Telegram for messaging-based finance management.
            </p>
            <div className="mt-4 rounded-md bg-gray-50 p-4 text-sm text-gray-700">
              <p className="font-medium">Setup instructions:</p>
              <ol className="mt-2 list-decimal list-inside space-y-1">
                <li>Message @BotFather on Telegram and create a new bot with /newbot</li>
                <li>Copy the bot token</li>
                <li>
                  Set <code className="bg-gray-200 px-1 rounded">TELEGRAM_BOT_TOKEN</code> in your .env
                  file
                </li>
                <li>
                  Restart:{" "}
                  <code className="bg-gray-200 px-1 rounded">docker compose restart agent-bot</code>
                </li>
              </ol>
            </div>
          </div>

          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-lg font-semibold text-gray-900">WhatsApp</h3>
            <p className="mt-2 text-sm text-gray-600">
              Connect your WhatsApp account using the Baileys bridge.
            </p>
            <div className="mt-4 rounded-md bg-gray-50 p-4 text-sm text-gray-700">
              <p className="font-medium">Setup instructions:</p>
              <ol className="mt-2 list-decimal list-inside space-y-1">
                <li>
                  Start with WhatsApp profile:{" "}
                  <code className="bg-gray-200 px-1 rounded">docker compose --profile whatsapp up -d</code>
                </li>
                <li>
                  Run:{" "}
                  <code className="bg-gray-200 px-1 rounded">
                    docker compose exec whatsapp-bridge npm run login
                  </code>
                </li>
                <li>Scan the QR code with WhatsApp &rarr; Settings &rarr; Linked Devices</li>
              </ol>
            </div>
          </div>
        </div>
      )}

      {activeTab === "system" && (
        <div className="rounded-lg bg-white p-6 shadow space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">System</h2>
          <div>
            <label className="block text-sm font-medium text-gray-500">Version</label>
            <p className="mt-1 text-gray-900">0.1.0</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">API Health</label>
            <div className="mt-1 flex items-center gap-3">
              <button
                onClick={checkHealth}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
              >
                Check Health
              </button>
              {healthStatus && (
                <span
                  className={`text-sm ${
                    healthStatus.startsWith("Healthy") ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {healthStatus}
                </span>
              )}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Database URL</label>
            <p className="mt-1 rounded-md bg-gray-50 px-3 py-2 text-gray-900 font-mono text-sm">
              postgresql://***:***@postgres:5432/fluxfinance
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
