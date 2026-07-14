import type { CourseAccessRule } from "./courseAccessTypes";

export type LectureAvailabilityState = "draft" | "hidden" | "scheduled" | "available";

export function editableAccessRule(rule: CourseAccessRule): CourseAccessRule {
  return {
    ...rule,
    audience: rule.audience === "public" ? "platform_authenticated" : rule.audience,
    publication_at: rule.publication_mode === "custom" ? rule.publication_at : null,
  };
}

export function lectureAvailability(
  rule: CourseAccessRule,
  lectureDate: string,
  published: boolean,
  now = new Date(),
): { availableAt: Date | null; state: LectureAvailabilityState } {
  if (!published) return { availableAt: accessDate(rule, lectureDate, now), state: "draft" };
  if (rule.audience === "instructors_only" || rule.publication_mode === "hidden") {
    return { availableAt: null, state: "hidden" };
  }
  const availableAt = accessDate(rule, lectureDate, now);
  if (!availableAt) return { availableAt: null, state: "hidden" };
  return { availableAt, state: availableAt.getTime() > now.getTime() ? "scheduled" : "available" };
}

export function accessDate(rule: CourseAccessRule, lectureDate: string, now = new Date()) {
  if (rule.publication_mode === "hidden") return null;
  const lectureFloor = berlinLectureStart(lectureDate);
  if (!lectureFloor) return null;
  const requestedValue =
    rule.publication_mode === "custom"
      ? rule.publication_at
      : rule.publication_mode === "published_now"
        ? (rule.publication_at ?? now.toISOString())
        : lectureFloor.toISOString();
  const requested = new Date(requestedValue ?? "");
  if (Number.isNaN(requested.getTime())) return null;
  return new Date(Math.max(lectureFloor.getTime(), requested.getTime()));
}

export function formatAccessDate(value: Date, locale: string, includeTime: boolean) {
  return new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    dateStyle: "medium",
    timeZone: "Europe/Berlin",
    ...(includeTime ? { timeStyle: "short" as const } : {}),
  }).format(value);
}

export function formatRelativeAccess(value: Date, locale: string, now = new Date()) {
  const milliseconds = value.getTime() - now.getTime();
  const minutes = Math.max(1, Math.ceil(milliseconds / 60_000));
  const [amount, unit] =
    minutes >= 2_880
      ? [Math.ceil(minutes / 1_440), "day" as const]
      : minutes >= 120
        ? [Math.ceil(minutes / 60), "hour" as const]
        : [minutes, "minute" as const];
  return new Intl.RelativeTimeFormat(locale === "de" ? "de-DE" : "en", {
    numeric: "always",
  }).format(amount, unit);
}

export function datetimeLocalValue(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = datePartsInBerlin(date);
  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(parts.minute)}`;
}

export function publicationAtFromLocal(value: string) {
  if (!value) return null;
  const date = berlinDateTime(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function berlinLectureStart(value: string) {
  const date = berlinDateTime(`${value}T00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function berlinDateTime(value: string) {
  const [datePart, timePart] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = (timePart ?? "00:00").split(":").map(Number);
  if (!year || !month || !day || Number.isNaN(hour) || Number.isNaN(minute)) {
    return new Date(Number.NaN);
  }
  const utcGuess = Date.UTC(year, month - 1, day, hour, minute);
  const represented = datePartsInBerlin(new Date(utcGuess));
  const representedUtc = Date.UTC(
    represented.year,
    represented.month - 1,
    represented.day,
    represented.hour,
    represented.minute,
  );
  return new Date(utcGuess - (representedUtc - utcGuess));
}

function datePartsInBerlin(value: Date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "2-digit",
    timeZone: "Europe/Berlin",
    year: "numeric",
  }).formatToParts(value);
  const values = Object.fromEntries(parts.map((part) => [part.type, Number(part.value)]));
  return {
    day: values.day,
    hour: values.hour,
    minute: values.minute,
    month: values.month,
    year: values.year,
  };
}

function pad(value: number) {
  return String(value).padStart(2, "0");
}
