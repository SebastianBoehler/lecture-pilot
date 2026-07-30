import { deMessages } from "./i18nMessages.de";
import { enMessages } from "./i18nMessages.en";
import { courseAccessMessages } from "./courseAccessMessages";
import { interactiveComponentMessages } from "./interactiveComponentMessages";

export const messages = {
  en: { ...enMessages, ...courseAccessMessages.en, ...interactiveComponentMessages.en },
  de: { ...deMessages, ...courseAccessMessages.de, ...interactiveComponentMessages.de },
} as const;

export type MessageKey = keyof typeof messages.en;
