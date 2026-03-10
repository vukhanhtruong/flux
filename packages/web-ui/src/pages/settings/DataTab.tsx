import { useState, useEffect, useRef, useCallback } from "react";
import { Download, Upload, Trash2, HardDrive, Cloud, RefreshCw, Key, Save, Eye, EyeOff, CheckCircle2, AlertCircle, X } from "lucide-react";
import { api } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import { useProfile } from "../../context/ProfileContext";
import type { BackupMetadata, S3Config } from "../../types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export function DataTab() {
  const { profile } = useProfile();
  const [backups, setBackups] = useState<BackupMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [s3Config, setS3Config] = useState<S3Config>({
    s3_endpoint: "",
    s3_bucket: "",
    s3_region: "",
    s3_access_key: "",
    s3_secret_key: "",
  });
  const [s3Loading, setS3Loading] = useState(false);
  const [s3Saving, setS3Saving] = useState(false);
  const [showAccessKey, setShowAccessKey] = useState(false);
  const [showSecretKey, setShowSecretKey] = useState(false);

  const loadS3Config = useCallback(async () => {
    setS3Loading(true);
    try {
      const config = await api.getBackupConfig();
      setS3Config(config);
    } catch {
      // FLUX_SECRET_KEY not set or endpoint unavailable — leave defaults
    } finally {
      setS3Loading(false);
    }
  }, []);

  async function handleSaveS3Config() {
    setS3Saving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await api.updateBackupConfig(s3Config);
      showSuccess("S3 configuration saved successfully");
    } catch (err) {
      setError(String(err));
    } finally {
      setS3Saving(false);
    }
  }

  const loadBackups = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listBackups();
      setBackups(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBackups();
    loadS3Config();
  }, [loadBackups, loadS3Config]);

  function showSuccess(msg: string) {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 4000);
  }

  const s3Configured = !!(s3Config.s3_endpoint && s3Config.s3_bucket && s3Config.s3_access_key && s3Config.s3_secret_key);

  async function handleCreateBackup(storage: "local" | "s3" = "local") {
    setCreating(true);
    setError(null);
    try {
      const backup = await api.createBackup(storage);
      showSuccess(`Backup created: ${backup.filename} (${storage})`);
      await loadBackups();
    } catch (err) {
      setError(String(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(backup: BackupMetadata) {
    setDeletingId(backup.id);
    setError(null);
    try {
      const key = backup.storage === "s3" && backup.s3_key ? backup.s3_key : backup.filename;
      await api.deleteBackup(key, backup.storage);
      showSuccess(`Backup deleted: ${backup.filename}`);
      await loadBackups();
    } catch (err) {
      setError(String(err));
    } finally {
      setDeletingId(null);
    }
  }

  async function handleRestore(backup: BackupMetadata) {
    setRestoring(true);
    setError(null);
    try {
      const key = backup.storage === "s3" && backup.s3_key ? backup.s3_key : backup.filename;
      const result = await api.restoreBackup(undefined, key, backup.storage);
      showSuccess(result.message || "Backup restored successfully");
      await loadBackups();
    } catch (err) {
      setError(String(err));
    } finally {
      setRestoring(false);
    }
  }

  async function handleFileUpload(file: File) {
    setRestoring(true);
    setError(null);
    try {
      const result = await api.restoreBackup(file);
      showSuccess(result.message || "Backup restored from file");
      await loadBackups();
    } catch (err) {
      setError(String(err));
    } finally {
      setRestoring(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave() {
    setDragOver(false);
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div className="space-y-8 relative">
      {/* Floating Notifications */}
      <div className="fixed top-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
        {successMessage && (
          <div className="animate-in slide-in-from-right-8 fade-in duration-300 flex items-center gap-3 px-4 py-3 bg-dark/95 backdrop-blur-md border border-emerald-500/20 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-xl pointer-events-auto shadow-emerald-500/10">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <p className="text-sm font-medium text-slate-200 pr-4">{successMessage}</p>
            <button
              onClick={() => setSuccessMessage(null)}
              className="p-1 hover:bg-white/10 rounded-md transition-colors text-slate-400 hover:text-white ml-auto"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {error && (
          <div className="animate-in slide-in-from-right-8 fade-in duration-300 flex items-center gap-3 px-4 py-3 bg-dark/95 backdrop-blur-md border border-red-500/20 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-xl pointer-events-auto shadow-red-500/10">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-sm font-medium text-slate-200 pr-4">{error}</p>
            <button
              onClick={() => setError(null)}
              className="p-1 hover:bg-white/10 rounded-md transition-colors text-slate-400 hover:text-white ml-auto"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Create Backup */}
      <div className="glass-card p-10 space-y-6 group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-1000"></div>
        <div className="relative">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-primary/10 rounded-xl group-hover:scale-110 group-hover:bg-primary/20 transition-all duration-300">
                  <HardDrive className="w-5 h-5 text-primary" />
                </div>
                <h2 className="text-xl font-bold text-white tracking-tight">Create Backup</h2>
              </div>
              <p className="text-sm text-slate-400 pl-14">
                Create a snapshot of your database including all transactions, budgets, goals, and settings.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 md:pl-0 pl-14">
              {creating ? (
                <button disabled className="btn-primary py-2.5 px-6 text-sm flex items-center gap-2 opacity-50 cursor-not-allowed">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Creating...
                </button>
              ) : s3Configured ? (
                <>
                  <button
                    onClick={() => handleCreateBackup("local")}
                    className="bg-dark border border-white/10 hover:bg-white/5 hover:border-white/20 text-white font-medium px-5 py-2.5 rounded-xl transition-all duration-200 cursor-pointer flex items-center gap-2.5 hover:-translate-y-0.5"
                  >
                    <HardDrive className="w-4 h-4 text-slate-400" />
                    Local Drive
                  </button>
                  <button
                    onClick={() => handleCreateBackup("s3")}
                    className="btn-primary py-2.5 px-6 text-sm flex items-center gap-2.5 hover:-translate-y-0.5"
                  >
                    <Cloud className="w-4 h-4" />
                    S3 Bucket
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleCreateBackup("local")}
                  className="btn-primary py-2.5 px-6 text-sm flex items-center gap-2 hover:-translate-y-0.5"
                >
                  <HardDrive className="w-4 h-4" />
                  Backup Now
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Backup List */}
      <div className="glass-card p-10 space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Cloud className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-white tracking-tight">Backup History</h2>
          </div>
          <button
            onClick={loadBackups}
            disabled={loading}
            className="btn-secondary py-1.5 px-4 text-xs flex items-center gap-2 h-9"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {loading && <p className="text-sm text-slate-500 italic">Loading backups...</p>}

        {!loading && backups.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 px-4 text-center border border-dashed border-white/5 rounded-2xl bg-dark/20 backdrop-blur-sm">
            <div className="p-4 bg-white/5 rounded-full mb-4">
              <HardDrive className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-white font-semibold mb-1">No backups available</h3>
            <p className="text-slate-500 text-sm max-w-sm">
              Create your first database snapshot to ensure your financial data is safely stored.
            </p>
          </div>
        )}

        {!loading && backups.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Filename</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Size</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Storage</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Created</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((backup) => (
                  <tr key={backup.id} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
                    <td className="py-3 pr-4 text-slate-300 font-mono text-xs max-w-[250px] truncate" title={backup.filename}>
                      {backup.filename}
                    </td>
                    <td className="py-3 pr-4 text-slate-400 text-xs">
                      {formatBytes(backup.size_bytes)}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-slate-400 uppercase">
                        {backup.storage === "s3" ? (
                          <Cloud className="w-3 h-3" />
                        ) : (
                          <HardDrive className="w-3 h-3" />
                        )}
                        {backup.storage}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-400 text-xs">
                      {formatDateTime(backup.created_at, profile.locale, profile.timezone)}
                    </td>
                    <td className="py-4">
                      <div className="flex items-center justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity duration-200">
                        <a
                          href={api.getBackupDownloadUrl(backup.filename)}
                          className="p-2 rounded-xl hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        <button
                          onClick={() => handleRestore(backup)}
                          disabled={restoring}
                          className="p-2 rounded-xl hover:bg-emerald-500/10 text-slate-400 hover:text-emerald-400 transition-all disabled:opacity-50"
                          title="Restore"
                        >
                          <RefreshCw className={`w-4 h-4 ${restoring ? "animate-spin text-emerald-400" : ""}`} />
                        </button>
                        <button
                          onClick={() => handleDelete(backup)}
                          disabled={deletingId === backup.id}
                          className="p-2 rounded-xl hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-all disabled:opacity-50"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Restore from File */}
      <div className="glass-card p-10 space-y-6 group">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-secondary/10 rounded-xl group-hover:bg-secondary/20 transition-all duration-300">
            <Upload className="w-5 h-5 text-secondary" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Restore from File</h2>
        </div>
        <p className="text-sm text-slate-400">
          Upload a backup file to restore your data. This will carefully replace all current data.
        </p>
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`relative overflow-hidden border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 group/dropzone ${
            dragOver
              ? "border-secondary bg-secondary/10 scale-[1.02]"
              : "border-white/10 hover:border-white/20 hover:bg-white/5"
          }`}
        >
          {dragOver && (
            <div className="absolute inset-0 bg-gradient-to-t from-secondary/10 to-transparent animate-pulse pointer-events-none"></div>
          )}
          
          <div className={`transform transition-all duration-300 ${dragOver ? "-translate-y-2 text-secondary" : "group-hover/dropzone:-translate-y-2 text-slate-600 group-hover/dropzone:text-slate-400"}`}>
            <Upload className="w-10 h-10 mx-auto mb-4" />
          </div>
          
          <p className="text-sm text-slate-300 mb-2 font-medium">
            {restoring ? (
              <span className="flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Restoring database...
              </span>
            ) : dragOver ? (
              "Drop to restore..."
            ) : (
              "Drag and drop a backup file here, or click to browse"
            )}
          </p>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
            .zip files supported
          </p>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileInputChange}
            className="hidden"
            accept=".zip"
          />
        </div>
      </div>

      {/* S3 Configuration */}
      <div className="glass-card p-10 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
          <div className="p-2.5 bg-secondary/10 rounded-xl group-hover:bg-secondary/20 transition-all duration-300">
            <Key className="w-5 h-5 text-secondary" />
          </div>
            <h2 className="text-xl font-bold text-white tracking-tight">S3 Storage</h2>
          </div>
        </div>
        <p className="text-sm text-slate-400">
          Configure S3-compatible storage (AWS S3, Cloudflare R2, MinIO) for remote backups.
          Credentials are encrypted with your <code className="text-xs bg-white/5 px-1.5 py-0.5 rounded">FLUX_SECRET_KEY</code>.
        </p>

        {/* Removed static S3 alerts since floating alerts are used globally */}

        {s3Loading ? (
          <p className="text-sm text-slate-500 italic">Loading configuration...</p>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Endpoint URL
                </label>
                <input
                  type="text"
                  value={s3Config.s3_endpoint}
                  onChange={(e) => setS3Config({ ...s3Config, s3_endpoint: e.target.value })}
                  placeholder="https://xxx.r2.cloudflarestorage.com"
                  className="w-full bg-dark border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary/50 focus:bg-white/5 transition-colors text-sm"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Bucket Name
                </label>
                <input
                  type="text"
                  value={s3Config.s3_bucket}
                  onChange={(e) => setS3Config({ ...s3Config, s3_bucket: e.target.value })}
                  placeholder="flux-backups"
                  className="w-full bg-dark border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary/50 focus:bg-white/5 transition-colors text-sm"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Region
                </label>
                <input
                  type="text"
                  value={s3Config.s3_region}
                  onChange={(e) => setS3Config({ ...s3Config, s3_region: e.target.value })}
                  placeholder="auto"
                  className="w-full bg-dark border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary/50 focus:bg-white/5 transition-colors text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Access Key
                </label>
                <div className="relative">
                  <input
                    type={showAccessKey ? "text" : "password"}
                    value={s3Config.s3_access_key}
                    onChange={(e) => setS3Config({ ...s3Config, s3_access_key: e.target.value })}
                    placeholder="••••••••••••••••"
                    className="w-full bg-dark border border-white/10 rounded-xl pl-4 pr-10 py-3 text-white outline-none focus:border-primary/50 focus:bg-white/5 transition-colors text-sm font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowAccessKey(!showAccessKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {showAccessKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500">
                  Secret Key
                </label>
                <div className="relative">
                  <input
                    type={showSecretKey ? "text" : "password"}
                    value={s3Config.s3_secret_key}
                    onChange={(e) => setS3Config({ ...s3Config, s3_secret_key: e.target.value })}
                    placeholder="••••••••••••••••"
                    className="w-full bg-dark border border-white/10 rounded-xl pl-4 pr-10 py-3 text-white outline-none focus:border-primary/50 focus:bg-white/5 transition-colors text-sm font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecretKey(!showSecretKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {showSecretKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleSaveS3Config}
                disabled={s3Saving}
                className="btn-primary py-2 px-6 text-sm flex items-center gap-2 disabled:opacity-50"
              >
                {s3Saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Configuration
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
