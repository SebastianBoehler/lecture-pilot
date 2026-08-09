import { deMessages } from "./i18nMessages.de";
import { enMessages } from "./i18nMessages.en";
import { courseAccessMessages } from "./courseAccessMessages";
import { interactiveComponentMessages } from "./interactiveComponentMessages";
import { learnerStateMessages } from "./learnerStateMessages";
import { learningAttemptMessages } from "./learningAttemptMessages";
import { reviewQueueMessages } from "./reviewQueueMessages";

export const messages = {
  en: {
    ...enMessages,
    ...courseAccessMessages.en,
    ...interactiveComponentMessages.en,
    ...learnerStateMessages.en,
    ...learningAttemptMessages.en,
    ...reviewQueueMessages.en,
  },
  de: {
    ...deMessages,
    ...courseAccessMessages.de,
    ...interactiveComponentMessages.de,
    ...learnerStateMessages.de,
    ...learningAttemptMessages.de,
    ...reviewQueueMessages.de,
  },
} as const;

export type MessageKey = keyof typeof messages.en;
