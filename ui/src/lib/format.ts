/** Currency and percent formatting helpers. */

export function formatUSD(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPct(value: number, decimals = 1): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}%`;
}

export function formatRelativeTime(isoString: string): string {
  const delta = new Date(isoString).getTime() - Date.now();
  const abs = Math.abs(delta);
  const sign = delta < 0 ? "ago" : "left";
  if (abs < 60_000) return `<1m ${sign}`;
  if (abs < 3_600_000) return `${Math.floor(abs / 60_000)}m ${sign}`;
  if (abs < 86_400_000) return `${Math.floor(abs / 3_600_000)}h ${sign}`;
  return `${Math.floor(abs / 86_400_000)}d ${sign}`;
}
