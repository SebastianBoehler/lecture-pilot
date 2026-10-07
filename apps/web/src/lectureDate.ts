import type { Locale } from "./i18nContext";

/** Formats an ISO calendar date (YYYY-MM-DD) for learners, e.g. "Wed, 26 Aug 2026". */
export function formatLectureDate(date: string, locale: Locale) {
  const parsed = new Date(`${date}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(parsed.getTime())) return date;
  return new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}
