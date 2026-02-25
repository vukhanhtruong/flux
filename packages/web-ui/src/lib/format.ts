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

export function formatDate(value: string, locale: string, timezone: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale || "en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: timezone || "UTC",
  }).format(date);
}
