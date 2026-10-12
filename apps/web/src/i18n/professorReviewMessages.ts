/** Draft-review details: reviewed task variants and AI teaching-implementation changes. */
export const professorReviewMessages = {
  en: {
    "review.taskBank.title": "Fresh reviewed task variants ({count})",
    "review.taskBank.help":
      "These tasks preserve the goal and rubric. Learners receive a fresh variant after support; future wording stays hidden from their learning path.",
    "review.taskBank.independent": "Independent check",
    "review.taskBank.delayed": "Delayed review",
    "review.taskBank.surface": "Changed surface:",
    "review.taskBank.numeric": "Numeric consistency checks",
    "review.taskBank.tolerance": "tolerance {value}",
    "review.changes.title": "Teaching implementation changes",
    "review.changes.load": "Inspect current implementation changes",
    "review.changes.loading": "Loading changes…",
    "review.changes.failed": "Implementation changes could not be loaded.",
    "review.changes.none": "No recorded implementation change is available for this revision.",
    "review.changes.reason": "Recorded reason:",
    "review.changes.noReason": "No repair reason was recorded for this change.",
    "review.changes.help":
      "These are exact changes to teaching under the approved goals. Review their correctness against the sources.",
    "review.changes.before": "Before",
    "review.changes.after": "After",
    "review.changes.unset": "Not previously set",
  },
  de: {
    "review.taskBank.title": "Neue geprüfte Aufgabenvarianten ({count})",
    "review.taskBank.help":
      "Diese Aufgaben erhalten Lernziel und Bewertungsraster. Nach einer Hilfe erhalten Studierende eine neue Variante; spätere Formulierungen bleiben in ihrem Lernpfad verborgen.",
    "review.taskBank.independent": "Eigenständige Prüfung",
    "review.taskBank.delayed": "Spätere Wiederholung",
    "review.taskBank.surface": "Geänderte Oberfläche:",
    "review.taskBank.numeric": "Numerische Konsistenzprüfungen",
    "review.taskBank.tolerance": "Toleranz {value}",
    "review.changes.title": "Änderungen an der Lehrumsetzung",
    "review.changes.load": "Aktuelle Änderungen ansehen",
    "review.changes.loading": "Änderungen werden geladen…",
    "review.changes.failed": "Die Änderungen konnten nicht geladen werden.",
    "review.changes.none": "Für diese Revision ist keine Änderung erfasst.",
    "review.changes.reason": "Erfasster Grund:",
    "review.changes.noReason": "Für diese Änderung wurde kein Reparaturgrund erfasst.",
    "review.changes.help":
      "Dies sind die genauen Änderungen an der Lehre unter den freigegebenen Lernzielen. Prüfe ihre Richtigkeit anhand der Quellen.",
    "review.changes.before": "Vorher",
    "review.changes.after": "Nachher",
    "review.changes.unset": "Zuvor nicht festgelegt",
  },
} as const;
