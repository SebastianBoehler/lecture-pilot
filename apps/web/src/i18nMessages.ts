import { deMessages } from "./i18nMessages.de";
import { enMessages, type MessageKey } from "./i18nMessages.en";

export const messages = {
  en: enMessages,
  de: deMessages,
} as const;

export type { MessageKey };
