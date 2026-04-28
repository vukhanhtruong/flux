import { useState, useEffect, useCallback } from "react";
import { Bot, Sparkles, Server, Key, Save, Plus, AlertCircle, CheckCircle, X } from "lucide-react";
import { api } from "../../lib/api";
import { USER_ID } from "../../lib/constants";
import type { LlmConfig, LlmProvider, LlmConfigUpdate } from "../../types";

const PROVIDERS: { value: LlmProvider; label: string; defaultModel: string }[] = [
  { value: "anthropic", label: "Anthropic", defaultModel: "claude-sonnet-4-6" },
  { value: "openai", label: "OpenAI", defaultModel: "gpt-4o" },
  { value: "openrouter", label: "OpenRouter", defaultModel: "anthropic/claude-3.5-sonnet" },
  { value: "ollama", label: "Ollama (Local)", defaultModel: "llama3.2" },
  { value: "custom", label: "Custom Provider", defaultModel: "" },
];

const DEFAULT_BASE_URLS: Record<LlmProvider, string> = {
  anthropic: "",
  openai: "",
  openrouter: "https://openrouter.ai/api/v1",
  ollama: "http://localhost:11434/v1",
  custom: "",
};

export function AITab() {
  const [config, setConfig] = useState<LlmConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const [formProvider, setFormProvider] = useState<LlmProvider>("anthropic");
  const [formModel, setFormModel] = useState("claude-sonnet-4-6");
  const [formBaseUrl, setFormBaseUrl] = useState("");
  const [formApiKey, setFormApiKey] = useState("");

  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLlmConfig(USER_ID);
      setConfig(data);
      if (data) {
        setFormProvider(data.provider as LlmProvider);
        setFormModel(data.model);
        setFormBaseUrl(data.base_url || "");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleProviderChange = (provider: LlmProvider) => {
    setFormProvider(provider);
    const providerConfig = PROVIDERS.find((p) => p.value === provider);
    if (providerConfig) {
      setFormModel(providerConfig.defaultModel);
    }
    setFormBaseUrl(DEFAULT_BASE_URLS[provider]);
  };

  const handleSave = async () => {
    if (!formModel.trim()) {
      setError("Model name is required");
      return;
    }
    if (!config && !formApiKey.trim()) {
      setError("API key is required for new configuration");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const update: LlmConfigUpdate = {
        provider: formProvider,
        model: formModel.trim(),
        base_url: formBaseUrl.trim() || null,
      };
      if (formApiKey.trim()) {
        update.api_key = formApiKey.trim();
      }

      const result = await api.updateLlmConfig(USER_ID, update);
      setConfig(result);
      setEditing(false);
      setFormApiKey("");
      setSuccess("AI configuration saved successfully");
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    if (config) {
      setFormProvider(config.provider as LlmProvider);
      setFormModel(config.model);
      setFormBaseUrl(config.base_url || "");
    }
    setFormApiKey("");
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setFormApiKey("");
    if (config) {
      setFormProvider(config.provider as LlmProvider);
      setFormModel(config.model);
      setFormBaseUrl(config.base_url || "");
    }
  };

  if (loading) {
    return (
      <div className="glass-card p-6 md:p-8 lg:p-10">
        <p className="text-sm text-slate-500 italic">Loading AI configuration...</p>
      </div>
    );
  }

  if (!config && !editing) {
    return (
      <div className="glass-card p-6 md:p-8 lg:p-10">
        <div className="text-center py-12">
          <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">No AI Configuration</h3>
          <p className="text-sm text-slate-400 mb-6">
            Configure your AI provider to enable the assistant features.
          </p>
          <button
            onClick={() => setEditing(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Configure AI
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 md:space-y-8">
      <div className="glass-card p-6 md:p-8 lg:p-10 space-y-6 md:space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-white tracking-tight">AI Configuration</h2>
          </div>
          {config && !editing && (
            <button onClick={handleStartEdit} className="btn-secondary py-1.5 px-4 text-xs">
              Edit
            </button>
          )}
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {!editing && config && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
            <div className="space-y-2">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                Provider
              </label>
              <div className="flex items-center gap-2 text-slate-300">
                <Sparkles className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium capitalize">{config.provider}</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                Model
              </label>
              <p className="text-sm text-slate-300 font-mono">{config.model}</p>
            </div>

            <div className="space-y-2">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                Base URL
              </label>
              <p className="text-sm text-slate-400">{config.base_url || "(default)"}</p>
            </div>

            <div className="space-y-2">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                API Key
              </label>
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-slate-500" />
                <span className="text-sm text-slate-400 font-mono">{config.api_key_masked}</span>
              </div>
            </div>
          </div>
        )}

        {editing && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Provider
                </label>
                <select
                  value={formProvider}
                  onChange={(e) => handleProviderChange(e.target.value as LlmProvider)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12 appearance-none"
                >
                  {PROVIDERS.map((p) => (
                    <option key={p.value} value={p.value} className="bg-dark">
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label htmlFor="model" className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Model
                </label>
                <input
                  id="model"
                  type="text"
                  value={formModel}
                  onChange={(e) => setFormModel(e.target.value)}
                  placeholder="e.g. claude-sonnet-4-6, gpt-4o"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Base URL <span className="text-slate-600">(optional)</span>
                </label>
                <div className="relative">
                  <Server className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={formBaseUrl}
                    onChange={(e) => setFormBaseUrl(e.target.value)}
                    placeholder="Leave empty for default endpoint"
                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12"
                  />
                </div>
              </div>

              <div className="space-y-2 md:col-span-2">
                <label htmlFor="apiKey" className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  API Key {config && <span className="text-slate-600">(leave empty to keep current)</span>}
                </label>
                <div className="relative">
                  <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    id="apiKey"
                    type="password"
                    value={formApiKey}
                    onChange={(e) => setFormApiKey(e.target.value)}
                    placeholder={config ? "Enter new API key or leave empty" : "Enter your API key"}
                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white outline-none focus:border-primary/50 transition-colors h-12"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 justify-end pt-4">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
              >
                {saving ? (
                  <span className="w-4 h-4 border-2 border-dark border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save Configuration
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Success toast */}
      {success && (
        <div className="fixed bottom-6 right-6 z-[110] animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-xl rounded-xl px-5 py-3 shadow-lg">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-sm text-emerald-300 font-medium">{success}</span>
            <button onClick={() => setSuccess(null)} className="text-emerald-400/60 hover:text-emerald-300 transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
