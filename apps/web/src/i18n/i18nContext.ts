import { createContext } from "react";
import type { messages, MessageKey } from "./i18nMessages";

export type Locale = keyof typeof messages;

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, params?: Record<string, string | number>) => string;
};

export const I18nContext = createContext<I18nContextValue | null>(null);
