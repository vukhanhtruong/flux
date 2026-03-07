import { useState, useEffect, useRef, useCallback } from "react";
import { Download, Upload, Trash2, HardDrive, Cloud, RefreshCw } from "lucide-react";
import { api } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import { useProfile } from "../../context/ProfileContext";
import type { BackupMetadata } from "../../types";

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
  }, [loadBackups]);

  function showSuccess(msg: string) {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 4000);
  }

  async function handleCreateBackup() {
    setCreating(true);
    setError(null);
    try {
      const backup = await api.createBackup("local");
      showSuccess(`Backup created: ${backup.filename}`);
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
      await api.deleteBackup(backup.id, backup.storage);
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
      const result = await api.restoreBackup(undefined, backup.id);
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
    <div className="space-y-8">
      {successMessage && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-sm text-emerald-400">
          {successMessage}
        </div>
      )}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Create Backup */}
      <div className="glass-card p-10 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <HardDrive className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold text-white tracking-tight">Create Backup</h2>
          </div>
          <button
            onClick={handleCreateBackup}
            disabled={creating}
            className="btn-primary py-2 px-6 text-sm flex items-center gap-2 disabled:opacity-50"
          >
            {creating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <HardDrive className="w-4 h-4" />
                Backup Now
              </>
            )}
          </button>
        </div>
        <p className="text-sm text-slate-400">
          Create a snapshot of your database. Backups include all transactions, budgets, goals,
          subscriptions, and settings.
        </p>
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
          <div className="text-center py-16">
            <HardDrive className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-500 text-sm">No backups found. Create your first backup above.</p>
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
                  <tr key={backup.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
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
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <a
                          href={api.getBackupDownloadUrl(backup.filename)}
                          className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        <button
                          onClick={() => handleRestore(backup)}
                          disabled={restoring}
                          className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-primary transition-colors disabled:opacity-50"
                          title="Restore"
                        >
                          <RefreshCw className={`w-4 h-4 ${restoring ? "animate-spin" : ""}`} />
                        </button>
                        <button
                          onClick={() => handleDelete(backup)}
                          disabled={deletingId === backup.id}
                          className="p-1.5 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-colors disabled:opacity-50"
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
      <div className="glass-card p-10 space-y-6">
        <div className="flex items-center gap-3">
          <Upload className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-bold text-white tracking-tight">Restore from File</h2>
        </div>
        <p className="text-sm text-slate-400">
          Upload a backup file to restore your data. This will replace all current data.
        </p>
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
            dragOver
              ? "border-primary bg-primary/5"
              : "border-white/10 hover:border-white/20 hover:bg-white/5"
          }`}
        >
          <Upload className={`w-10 h-10 mx-auto mb-4 ${dragOver ? "text-primary" : "text-slate-600"}`} />
          <p className="text-sm text-slate-400 mb-1">
            {restoring ? "Restoring..." : "Drag and drop a backup file here, or click to browse"}
          </p>
          <p className="text-[10px] text-slate-600 uppercase tracking-widest font-bold">
            .db files supported
          </p>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileInputChange}
            className="hidden"
            accept=".db,.sqlite,.backup"
          />
        </div>
      </div>
    </div>
  );
}
