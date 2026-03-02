import { describe, expect, it } from "vitest";
import {
  computePortfolioTotal,
  computePerformance,
  upsertSnapshot,
  filterSnapshotsForRange,
  type PortfolioSnapshot,
} from "../assetsPerformance";

describe("assetsPerformance", () => {
  it("computes total from asset value and amount fields", () => {
    const total = computePortfolioTotal([
      { value: "100.50" },
      { amount: "49.50" },
      { value: "invalid" },
    ]);

    expect(total).toBe(150);
  });

  it("does not append new snapshot if interval is too short", () => {
    const start = 1_700_000_000_000;
    const points: PortfolioSnapshot[] = [{ timestamp: start, totalValue: 1000 }];

    const updated = upsertSnapshot(points, {
      now: start + 60 * 60 * 1000,
      totalValue: 1010,
      minIntervalMs: 6 * 60 * 60 * 1000,
      retentionMs: 365 * 24 * 60 * 60 * 1000,
    });

    expect(updated).toHaveLength(1);
    expect(updated[0].totalValue).toBe(1010);
  });

  it("computes range performance when baseline exists", () => {
    const now = 1_700_000_000_000;
    const day = 24 * 60 * 60 * 1000;
    const points: PortfolioSnapshot[] = [
      { timestamp: now - 8 * day, totalValue: 1000 },
      { timestamp: now - 7 * day, totalValue: 1100 },
      { timestamp: now, totalValue: 1200 },
    ];

    const result = computePerformance(points, { now, range: "7d" });

    expect(result).not.toBeNull();
    expect(result?.delta).toBe(100);
    expect(result?.deltaPct).toBeCloseTo(100 / 1100, 6);
  });

  it("returns null when not enough history for selected range", () => {
    const now = 1_700_000_000_000;
    const points: PortfolioSnapshot[] = [{ timestamp: now, totalValue: 1200 }];

    const result = computePerformance(points, { now, range: "30d" });

    expect(result).toBeNull();
  });

  it("filters snapshots for chart range", () => {
    const now = 1_700_000_000_000;
    const day = 24 * 60 * 60 * 1000;
    const points: PortfolioSnapshot[] = [
      { timestamp: now - 40 * day, totalValue: 900 },
      { timestamp: now - 10 * day, totalValue: 1000 },
      { timestamp: now - 2 * day, totalValue: 1100 },
      { timestamp: now, totalValue: 1200 },
    ];

    const result = filterSnapshotsForRange(points, { now, range: "30d" });

    expect(result).toHaveLength(3);
    expect(result[0].totalValue).toBe(1000);
  });
});
