export const examChoiceEn = {
  "practice.setup.choiceFormat": "Multiple-choice format",
  "practice.setup.singleAnswer": "Single answer",
  "practice.setup.multipleAnswers": "Multiple answers with deductions",
  "practice.multipleRule":
    "Select all correct options. Practice scoring: 4 points for the complete correct set; otherwise −1 per wrong selection and 0 for incomplete correct sets. Scores can be negative. Check your exam's official marking rule.",
  "practice.selectAll": "Select all correct options.",
  "practice.solutions.questionScore": "Score: {earned} / {available}",
} as const;

export const examChoiceDe: Record<keyof typeof examChoiceEn, string> = {
  "practice.setup.choiceFormat": "Multiple-Choice-Format",
  "practice.setup.singleAnswer": "Eine richtige Antwort",
  "practice.setup.multipleAnswers": "Mehrere Antworten mit Punktabzug",
  "practice.multipleRule":
    "Wähle alle richtigen Optionen. Übungswertung: 4 Punkte für die vollständig richtige Auswahl; sonst −1 pro falscher Auswahl und 0 für unvollständige richtige Auswahlen. Negative Werte sind möglich. Prüfe die offizielle Bewertungsregel deiner Klausur.",
  "practice.selectAll": "Wähle alle richtigen Optionen.",
  "practice.solutions.questionScore": "Punkte: {earned} / {available}",
};
