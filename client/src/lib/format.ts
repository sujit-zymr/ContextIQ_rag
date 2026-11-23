const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

const options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", year: "numeric" };
const dateOnlyFormatter = new Intl.DateTimeFormat("en-US", { ...options, timeZone: "UTC" });
const localFormatter = new Intl.DateTimeFormat("en-US", options);

/**
 * Formats a backend date as "Nov 18, 2026" (plan §7.7).
 * - Date-only values ("2026-01-15", document metadata) are formatted in UTC so
 *   they never shift by a day.
 * - Timestamps ("2026-11-18T09:30:00Z") are shown in the reader's time zone.
 * Unparseable input is returned unchanged.
 */
export function formatDate(value: string): string {
  const dateOnly = DATE_ONLY.test(value);
  const date = new Date(dateOnly ? `${value}T00:00:00Z` : value);
  if (Number.isNaN(date.getTime())) return value;
  return (dateOnly ? dateOnlyFormatter : localFormatter).format(date);
}
