import type { Asset } from "../types";

export type PerformanceRange = "24h" | "7d" | "30d" | "90d" | "1y" | "all";

export interface PortfolioSnapshot {
  timestamp: number;
  totalValue: number;
}

interface UpsertOptions {
  now: number;
  totalValue: number;
  minIntervalMs: number;
  retentionMs: number;
}

interface PerformanceOptions {
  now: number;
  range: PerformanceRange;
}

export interface PerformanceMetric {
  delta: number;
  deltaPct: number | null;
  baseline: number;
  current: number;
}

const PERFORMANCE_STORAGE_KEY = "flux:assets:performance:snapshots:v1";
const DEFAULT_MIN_INTERVAL_MS = 6 * 60 * 60 * 1000;
const DEFAULT_RETENTION_MS = 365 * 24 * 60 * 60 * 1000;

const RANGE_TO_MS: Record<Exclude<PerformanceRange, "all">, number> = {
  "24h": 24 * 60 * 60 * 1000,
  "7d": 7 * 24 * 60 * 60 * 1000,
  "30d": 30 * 24 * 60 * 60 * 1000,
  "90d": 90 * 24 * 60 * 60 * 1000,
  "1y": 365 * 24 * 60 * 60 * 1000,
};

export function computePortfolioTotal(assets: Array<Partial<Asset> & { amount?: string | number }>): number {
  const total = assets.reduce((sum, asset) => {
    const raw = asset.value ?? asset.amount ?? 0;
    const parsed = typeof raw === "number" ? raw : Number(raw);
    return Number.isFinite(parsed) ? sum + parsed : sum;
  }, 0);

  return Number(total.toFixed(2));
}

export function upsertSnapshot(points: PortfolioSnapshot[], options: UpsertOptions): PortfolioSnapshot[] {
  const { now, totalValue, minIntervalMs, retentionMs } = options;
  const sorted = [...points]
    .filter((point) => Number.isFinite(point.timestamp) && Number.isFinite(point.totalValue))
    .sort((a, b) => a.timestamp - b.timestamp);

  if (sorted.length === 0) {
    return [{ timestamp: now, totalValue }];
  }

  const last = sorted[sorted.length - 1];
  const shouldReplaceLast = now - last.timestamp < minIntervalMs;

  if (shouldReplaceLast) {
    sorted[sorted.length - 1] = { timestamp: now, totalValue };
  } else {
    sorted.push({ timestamp: now, totalValue });
  }

  const cutoff = now - retentionMs;
  return sorted.filter((point) => point.timestamp >= cutoff);
}

export function computePerformance(
  points: PortfolioSnapshot[],
  options: PerformanceOptions,
): PerformanceMetric | null {
  const { now, range } = options;
  const sorted = [...points].sort((a, b) => a.timestamp - b.timestamp);
  if (sorted.length < 2) return null;

  const current = sorted[sorted.length - 1].totalValue;
  const baseline = findBaseline(sorted, now, range);
  if (baseline == null) return null;

  const delta = Number((current - baseline).toFixed(2));
  const deltaPct = baseline > 0 ? (current - baseline) / baseline : null;

  return {
    delta,
    deltaPct,
    baseline,
    current,
  };
}

export function filterSnapshotsForRange(
  points: PortfolioSnapshot[],
  options: PerformanceOptions,
): PortfolioSnapshot[] {
  const { now, range } = options;
  const sorted = [...points].sort((a, b) => a.timestamp - b.timestamp);
  if (range === "all") return sorted;

  const cutoff = now - RANGE_TO_MS[range];
  return sorted.filter((point) => point.timestamp >= cutoff);
}

function findBaseline(points: PortfolioSnapshot[], now: number, range: PerformanceRange): number | null {
  if (range === "all") return points[0]?.totalValue ?? null;

  const target = now - RANGE_TO_MS[range];
  let baseline: number | null = null;
  for (const point of points) {
    if (point.timestamp <= target) {
      baseline = point.totalValue;
      continue;
    }
    break;
  }

  return baseline;
}

export function loadSnapshots(storage: Storage | null = resolveStorage()): PortfolioSnapshot[] {
  if (!storage) return [];

  const raw = storage.getItem(PERFORMANCE_STORAGE_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw) as PortfolioSnapshot[];
    return Array.isArray(parsed)
      ? parsed.filter((point) => Number.isFinite(point.timestamp) && Number.isFinite(point.totalValue))
      : [];
  } catch {
    return [];
  }
}

export function saveSnapshots(points: PortfolioSnapshot[], storage: Storage | null = resolveStorage()): void {
  if (!storage) return;
  storage.setItem(PERFORMANCE_STORAGE_KEY, JSON.stringify(points));
}

export function recordSnapshot(
  totalValue: number,
  now = Date.now(),
  storage: Storage | null = resolveStorage(),
): PortfolioSnapshot[] {
  const existing = loadSnapshots(storage);
  const updated = upsertSnapshot(existing, {
    now,
    totalValue,
    minIntervalMs: DEFAULT_MIN_INTERVAL_MS,
    retentionMs: DEFAULT_RETENTION_MS,
  });
  saveSnapshots(updated, storage);
  return updated;
}

function resolveStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}
