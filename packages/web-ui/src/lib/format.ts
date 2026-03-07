export function formatCurrency(
  value: string | number,
  currency: string,
  locale: string
): string {
  const amount = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(amount)) return "-";

  if (currency.toUpperCase() === "VND") {
    return `VND ${Math.round(amount).toLocaleString("en-US")}`;
  }

  try {
    return new Intl.NumberFormat(locale || "en-US", {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency || "USD"} ${amount.toFixed(2)}`;
  }
}

/**
 * Parse a SQLite UTC timestamp (e.g. "2026-03-07 12:46:36") into a Date.
 * Handles both ISO 8601 ("...T...Z") and SQLite space-separated formats.
 */
function parseUTCTimestamp(value: string): Date {
  // Replace space separator with T and ensure Z suffix for UTC
  let normalized = value.replace(" ", "T");
  if (!normalized.endsWith("Z") && !normalized.includes("+") && !normalized.includes("-", 10)) {
    normalized += "Z";
  }
  return new Date(normalized);
}

export function formatDate(value: string, locale: string, timezone: string): string {
  const date = parseUTCTimestamp(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale || "en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: timezone || "UTC",
  }).format(date);
}

export function formatDateTime(value: string, locale: string, timezone: string): string {
  const date = parseUTCTimestamp(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale || "en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: timezone || "UTC",
  }).format(date);
}
