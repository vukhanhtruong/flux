import { describe, it, expect } from "vitest";
import { formatCurrency, formatDate, formatDateTime } from "./format";

describe("formatting utilities", () => {
  it("formats currency correctly", () => {
    expect(formatCurrency(1000, "USD", "en-US")).toBe("$1,000.00");
    expect(formatCurrency(1000, "VND", "vi-VN")).toBe("VND 1,000"); 
  });

  it("handles empty or invalid inputs for currency", () => {
    expect(formatCurrency("", "USD", "en-US")).toBe("$0.00");
    expect(formatCurrency(undefined as any, "USD", "en-US")).toBe("-");
    expect(formatCurrency(NaN, "USD", "en-US")).toBe("-");
  });

  it("formats date correctly", () => {
    const date = "2023-10-15T12:00:00Z";
    expect(formatDate(date, "en-US", "UTC")).toContain("10/15/2023");
  });

  it("formats datetime correctly", () => {
    const date = "2023-10-15T12:00:00Z";
    expect(formatDateTime(date, "en-US", "UTC")).toContain("10/15/2023");
    expect(formatDateTime(date, "en-US", "UTC")).toContain("12:00:00");
  });

  it("handles empty inputs for dates", () => {
    expect(formatDate("", "en-US", "UTC")).toBe("");
    expect(formatDateTime("", "en-US", "UTC")).toBe("");
  });
});
