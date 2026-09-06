import { outlineMessages } from "./outlineMessages";
import { learningIntentMessages } from "./learningIntentMessages";
import { tutorMessages } from "./tutorMessages";
import { deMessages } from "./i18nMessages.de";
import { enMessages } from "./i18nMessages.en";
import { courseAccessMessages } from "./courseAccessMessages";
import { interactiveComponentMessages } from "./interactiveComponentMessages";
import { learnerStateMessages } from "./learnerStateMessages";
import { learningAttemptMessages } from "./learningAttemptMessages";
import { reviewQueueMessages } from "./reviewQueueMessages";

export const messages = {
  en: {
    ...tutorMessages.en,
    ...outlineMessages.en,
    ...enMessages,
    ...learningIntentMessages.en,
    ...courseAccessMessages.en,
    ...interactiveComponentMessages.en,
    ...learnerStateMessages.en,
    ...learningAttemptMessages.en,
    ...reviewQueueMessages.en,
  },
  de: {
    ...tutorMessages.de,
    ...outlineMessages.de,
    ...deMessages,
    ...learningIntentMessages.de,
    ...courseAccessMessages.de,
    ...interactiveComponentMessages.de,
    ...learnerStateMessages.de,
    ...learningAttemptMessages.de,
    ...reviewQueueMessages.de,
  },
} as const;

export type MessageKey = keyof typeof messages.en;
