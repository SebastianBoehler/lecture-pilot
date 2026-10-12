import type { Locale } from "../i18n/i18nContext";

/**
 * Formats an ISO calendar date (YYYY-MM-DD), e.g. "Wed, 26 Aug 2026". The date is read and
 * formatted in UTC so it names the same calendar day in every viewer time zone; any other
 * value (including impossible dates) is returned unchanged.
 */
export function formatLectureDate(date: string, locale: Locale) {
  const parsed = new Date(`${date}T00:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    Number.isNaN(parsed.getTime()) ||
    parsed.toISOString().slice(0, 10) !== date
  ) {
    return date;
  }
  return new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}
