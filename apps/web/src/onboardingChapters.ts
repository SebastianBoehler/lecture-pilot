import type { Locale } from "./i18n";

export const ONBOARDING_MEDIA = "/media/onboarding/2026-09-07-r3";

const starts = [0, 19, 99.125, 136.792, 197.792, 285.958, 333, 417.167, 486.792, 550.417];

const content = {
  en: [
    [
      "Welcome and sign-in",
      "Sign in with your university account and open the professor workspace.",
      "Use the course title from Alma or ILIAS so students can recognize it.",
    ],
    [
      "Create a course and upload materials",
      "Create the course and upload your existing teaching materials.",
      "Check the proposed lectures and dates before continuing.",
    ],
    [
      "Review source assignments",
      "Review which files belong to each lecture, the whole course, or are not used.",
      "Confirm the assignments; then choose optional videos or continue without them.",
    ],
    [
      "Review learning goals",
      "Inspect the source-backed outcomes for each lecture and edit them where needed.",
      "Approve every lecture’s goals before generating the teaching material.",
    ],
    [
      "Review and publish the canvases",
      "Preview the explanations, source references, and practice in each generated canvas.",
      "Approve the drafts, publish the workspaces, and check student access dates.",
    ],
    [
      "Student access and study tools",
      "Open an available lecture as a student and choose your attendance mode.",
      "Explore the canvas and exam-readiness checks from the learner’s perspective.",
    ],
    [
      "Tutor help on the canvas",
      "Try a checkpoint, explain your reasoning, and ask for help where you get stuck.",
      "The tutor can direct you to the relevant passage and provide targeted explanations.",
    ],
    [
      "Personalized explanations",
      "Ask for an example that makes sense to you, such as the dog-and-cat analogy.",
      "Request a new section to keep that explanation in your private learner canvas.",
    ],
    [
      "Generate and download a practice exam",
      "Choose the exam length and stay on the page while the exam is generated.",
      "Take it in the browser or download the exam; use the separate solutions for self-review.",
    ],
    [
      "Learning goals guide the tutor",
      "Ask what to work on next and connect the tutor’s guidance to the course goals.",
      "Professor-approved outcomes provide the direction for teaching and practice.",
    ],
  ],
  de: [
    [
      "Willkommen und Anmeldung",
      "Melden Sie sich mit Ihrem Universitätskonto an und öffnen Sie den Lehrendenbereich.",
      "Verwenden Sie den Kurstitel aus Alma oder ILIAS, damit Studierende ihn wiedererkennen.",
    ],
    [
      "Kurs erstellen und Materialien hochladen",
      "Erstellen Sie den Kurs und laden Sie Ihre vorhandenen Lehrmaterialien hoch.",
      "Prüfen Sie die vorgeschlagenen Vorlesungen und Termine, bevor Sie fortfahren.",
    ],
    [
      "Quellenzuordnung prüfen",
      "Prüfen Sie, welche Dateien zu einer Vorlesung, zum gesamten Kurs oder zu den nicht verwendeten Dateien gehören.",
      "Bestätigen Sie die Zuordnung. Wählen Sie anschließend optionale Videos oder fahren Sie ohne diese fort.",
    ],
    [
      "Lernziele prüfen",
      "Prüfen Sie die quellenbasierten Lernziele jeder Vorlesung und bearbeiten Sie diese bei Bedarf.",
      "Geben Sie alle Lernziele frei, bevor die Lehrmaterialien erstellt werden.",
    ],
    [
      "Lerninhalte prüfen und veröffentlichen",
      "Prüfen Sie Erklärungen, Quellenverweise und Übungen in jedem erstellten Canvas.",
      "Geben Sie die Entwürfe frei, veröffentlichen Sie die Lernbereiche und prüfen Sie die Zugangstermine.",
    ],
    [
      "Studierendenzugang und Lernwerkzeuge",
      "Öffnen Sie eine verfügbare Vorlesung als Studierender und wählen Sie den Anwesenheitsmodus.",
      "Erkunden Sie den Canvas und die Prüfungsreife-Checks aus Sicht der Lernenden.",
    ],
    [
      "Tutorhilfe im Canvas",
      "Bearbeiten Sie einen Checkpoint, erklären Sie Ihren Lösungsweg und bitten Sie bei Schwierigkeiten um Hilfe.",
      "Der Tutor kann zur passenden Textstelle führen und gezielt erklären.",
    ],
    [
      "Persönliche Erklärungen",
      "Bitten Sie um ein verständliches Beispiel, etwa mit Hunden und Katzen.",
      "Fordern Sie einen neuen Abschnitt an, um die Erklärung im privaten Lern-Canvas zu behalten.",
    ],
    [
      "Übungsklausur erstellen und herunterladen",
      "Wählen Sie den Umfang und bleiben Sie während der Erstellung auf der Seite.",
      "Bearbeiten Sie die Klausur im Browser oder laden Sie sie herunter. Die separaten Lösungen dienen der Selbstkontrolle.",
    ],
    [
      "Lernziele leiten den Tutor",
      "Fragen Sie nach dem nächsten Lernschritt und verbinden Sie die Empfehlung mit den Kurszielen.",
      "Die freigegebenen Lernziele geben die Richtung für Erklärungen und Übungen vor.",
    ],
  ],
};

export function onboardingChapters(locale: Locale) {
  return content[locale].map(([title, action, result], index) => ({
    title,
    action,
    result,
    start: starts[index],
  }));
}
