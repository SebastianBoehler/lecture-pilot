import type { Locale } from "./i18n";

const LOCALE_STORAGE_KEY = "lecturepilot.locale";

export function readLocalePreference(): Locale {
  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  if (isLocale(stored)) return stored;
  return browserLocale();
}

export function writeLocalePreference(locale: Locale) {
  window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
}

function browserLocale(): Locale {
  const language = window.navigator.language.toLowerCase();
  return language.startsWith("de") ? "de" : "en";
}

function isLocale(value: string | null): value is Locale {
  return value === "en" || value === "de";
}
