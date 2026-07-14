import { deMessages } from "./i18nMessages.de";
import { enMessages } from "./i18nMessages.en";
import { courseAccessMessages } from "./courseAccessMessages";

export const messages = {
  en: { ...enMessages, ...courseAccessMessages.en },
  de: { ...deMessages, ...courseAccessMessages.de },
} as const;

export type MessageKey = keyof typeof messages.en;
