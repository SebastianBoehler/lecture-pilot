import { useContext, useMemo, type ReactNode } from "react";

import { messages, type MessageKey } from "./i18nMessages";

import { I18nContext, type Locale } from "./i18nContext";
export type { Locale } from "./i18nContext";

export function I18nProvider({
  children,
  locale,
  setLocale,
}: {
  children: ReactNode;
  locale: Locale;
  setLocale: (locale: Locale) => void;
}) {
  const value = useMemo(() => ({ locale, setLocale, t: translate(locale) }), [locale, setLocale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider.");
  }
  return context;
}

function translate(locale: Locale) {
  return (key: MessageKey, params: Record<string, string | number> = {}) => {
    const template = messages[locale][key] ?? messages.en[key];
    return Object.entries(params).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
      template,
    );
  };
}
