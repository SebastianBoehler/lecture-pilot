import type { InfoArticleContent } from "./infoArticleTypes";

export const howItWorksContent: Record<"en" | "de", InfoArticleContent> = {
  en: {
    title: "How LecturePilot works",
    intro:
      "A place to work through your actual course material, ask for help where you get stuck, and check what you can do on your own.",
    sections: [
      {
        id: "students",
        title: "For students",
        paragraphs: [
          "The lecture canvas brings explanations, source references and practice together. The tutor can point to a passage, explain it differently, or add a personal example beside the material. You do not have to reconstruct your course in a new chat each time.",
          "Only published lectures that are already available to your account can be used. Course access and lecture dates are checked by the application.",
        ],
        steps: [
          "Open a lecture and attempt a checkpoint in your own words.",
          "If you get stuck, ask for a hint or explain which step is unclear.",
          "Work through the feedback. After supported work, use a fresh independent task to check your understanding.",
          "Return to the topic later and try again without your notes.",
        ],
        example:
          "“I understand the formula, but not why it works. Can you add a small numerical example here?”",
      },
      {
        id: "personal",
        title: "Your own notes, explanations and memory",
        paragraphs: [
          "Ask the tutor to annotate a passage: a marker beside the text reopens the comment. Annotations are private; they are not a public discussion with the class. Personalized sections and generated visuals also stay in your learner workspace.",
          "The tutor can save useful learning observations for this course, and preferences across courses. In your profile you can inspect and remove saved preferences or memory. The file workspace lets you inspect saved learner files. This is saved context, not a claim that the model remembers everything.",
        ],
      },
      {
        id: "exams",
        title: "Practice and exam preparation",
        paragraphs: [
          "A Before you begin card invites an optional first prediction. Save a short guess or skip, then revisit it after the explanation; it is private and ungraded. Checkpoints are small checks within a lecture. Independent attempts hide teaching, chat and notes so your answer reflects what you can do without that support. If no fresh reviewed task remains, the app tells you.",
          "Exam checks help you practise selected learning goals. Practice exams are a separate simulation with downloadable questions and solutions for self-review. Saved submissions can inform later tutor guidance; they are not server-graded university exams and do not automatically establish mastery.",
        ],
      },
      {
        id: "lecturers",
        title: "For lecturers",
        paragraphs: [
          "Start with the materials you already teach from. You decide the learning goals and what students may see. The AI develops explanations and practice within that approved intent; you review the actual result before publishing.",
        ],
        steps: [
          "Course: choose the course and its lecture structure.",
          "Materials: upload sources and review which files belong to each lecture, the whole course, or are not used.",
          "Media: choose supplementary videos or continue without them.",
          "Learning plan: review and approve the intended learning outcomes.",
          "Review & publish: generate the lecture canvases, inspect the student preview, approve the drafts and publish.",
        ],
        detail:
          "A course listed under Manage courses is not necessarily published. Students need a published workspace and eligible lecture access. If generation fails, retry the affected lecture; completed work can be retained. Changing sources or approved goals can require a new review.",
      },
      {
        id: "behind",
        title: "Behind the scenes",
        paragraphs: [
          "The model works through tools supplied by LecturePilot. This surrounding software—the agent harness—checks the account, course and lecture, reads permitted context, and validates changes before saving them. The browser never holds the model provider’s API key.",
          "The shared course stays separate from your private work. The tutor can read approved material but cannot rewrite it for everyone or open another learner’s workspace.",
        ],
        steps: [
          "Your question and relevant course context go through the backend to the model provider.",
          "The tutor can read permitted sources, focus a passage, and create learner-owned additions through tools.",
          "Validated additions, recent conversation and learning state are saved so you can continue later.",
        ],
      },
      {
        id: "limits",
        title: "What the tool can and cannot tell you",
        paragraphs: [
          "A fluent explanation can still be wrong. Open the source references, question unclear steps, and report problems using Feedback. Professor review and source checks help, but do not guarantee that every explanation or assessment is correct.",
          "Course analytics show learning signals across the course, not ordinary private chats or personal canvases. Supported answers and independent attempts have different meanings. These signals are not a university grade or proof of long-term retention.",
          "The teaching design is informed by learning research. LecturePilot’s own effect on learning still needs evaluation.",
        ],
      },
    ],
  },
  de: {
    title: "So funktioniert LecturePilot",
    intro:
      "Ein Ort, um deinen Vorlesungsstoff durchzuarbeiten, bei Schwierigkeiten gezielt nachzufragen und zu prüfen, was du schon selbstständig kannst.",
    sections: [
      {
        id: "students",
        title: "Für Studierende",
        paragraphs: [
          "Der Vorlesungs-Canvas verbindet Erklärungen, Quellen und Übungen. Der Tutor kann eine Stelle zeigen, sie anders erklären oder ein persönliches Beispiel direkt daneben ergänzen. Du musst deinen Kurs nicht in jedem neuen Chat wieder erklären.",
          "Nutzbar sind nur veröffentlichte Vorlesungen, die für dein Konto bereits verfügbar sind. Kurszugang und Vorlesungsdatum prüft die Anwendung.",
        ],
        steps: [
          "Öffne eine Vorlesung und versuche einen Checkpoint in eigenen Worten.",
          "Wenn du feststeckst, bitte um einen Hinweis oder beschreibe den unklaren Schritt.",
          "Arbeite mit dem Feedback weiter. Prüfe danach mit einer neuen, selbstständigen Aufgabe, ob du es ohne Hilfe kannst.",
          "Komm später auf das Thema zurück und versuche es erneut ohne Notizen.",
        ],
        example:
          "„Ich verstehe die Formel, aber nicht, warum sie funktioniert. Kannst du hier ein kleines Zahlenbeispiel ergänzen?“",
      },
      {
        id: "personal",
        title: "Deine Notizen, Erklärungen und Erinnerungen",
        paragraphs: [
          "Bitte den Tutor um eine Annotation zu einer Textstelle: Über den Marker am Rand öffnest du den Kommentar wieder. Annotationen sind privat, kein öffentlicher Austausch im Kurs. Auch persönliche Abschnitte und erzeugte Bilder bleiben in deinem Lernworkspace.",
          "Der Tutor kann Beobachtungen für diesen Kurs und Vorlieben über Kurse hinweg speichern. Im Profil kannst du gespeicherte Vorlieben und Erinnerungen ansehen und entfernen. Im Dateibereich findest du gespeicherte Lerndateien. Das ist gespeicherter Kontext, kein lückenloses Gedächtnis des Modells.",
        ],
      },
      {
        id: "exams",
        title: "Üben und auf Prüfungen vorbereiten",
        paragraphs: [
          "Die Karte Bevor du beginnst lädt zu einer freiwilligen ersten Vermutung ein. Speichere eine kurze Idee oder überspringe die Frage und greife sie nach der Erklärung wieder auf; sie bleibt privat und unbewertet. Checkpoints sind kurze Aufgaben innerhalb einer Vorlesung. Bei selbstständigen Versuchen werden Erklärungen, Chat und Notizen ausgeblendet. So zeigt deine Antwort, was du ohne diese Unterstützung kannst. Ist keine neue geprüfte Aufgabe mehr verfügbar, zeigt die App das an.",
          "Prüfungschecks helfen beim Üben ausgewählter Lernziele. Übungsklausuren sind eine separate Simulation mit herunterladbaren Aufgaben und Lösungen zur Selbstkontrolle. Gespeicherte Abgaben können spätere Tutorhilfe ergänzen; sie sind keine serverseitig benoteten Hochschulprüfungen und belegen nicht automatisch die Beherrschung eines Themas.",
        ],
      },
      {
        id: "lecturers",
        title: "Für Lehrende",
        paragraphs: [
          "Beginnen Sie mit Ihren vorhandenen Lehrmaterialien. Sie entscheiden über die Lernziele und die Freigabe. Die KI entwickelt dazu Erklärungen und Übungen; vor der Veröffentlichung prüfen Sie das konkrete Ergebnis.",
        ],
        steps: [
          "Kurs: Wählen Sie den Kurs und seine Vorlesungsstruktur.",
          "Materialien: Laden Sie Quellen hoch und prüfen Sie die Zuordnung zu Vorlesungen, zum gesamten Kurs oder zu „nicht verwendet“.",
          "Medien: Wählen Sie ergänzende Videos oder fahren Sie ohne Videos fort.",
          "Lernplan: Prüfen und bestätigen Sie die vorgesehenen Lernergebnisse.",
          "Prüfen & veröffentlichen: Lassen Sie die Inhalte erstellen, prüfen Sie die Studierendenansicht und geben Sie die Entwürfe zur Veröffentlichung frei.",
        ],
        detail:
          "Ein Kurs unter „Kurse verwalten“ ist nicht automatisch veröffentlicht. Studierende benötigen einen veröffentlichten Workspace und Zugang zur Vorlesung. Bei einem Generierungsfehler können Sie die betroffene Vorlesung erneut versuchen; fertige Arbeit kann erhalten bleiben. Änderungen an Quellen oder bestätigten Lernzielen können eine erneute Prüfung erfordern.",
      },
      {
        id: "behind",
        title: "Was im Hintergrund passiert",
        paragraphs: [
          "Das Modell arbeitet mit Werkzeugen von LecturePilot. Die umgebende Software – der Agent Harness – prüft Konto, Kurs und Vorlesung, liest erlaubten Kontext und validiert Änderungen vor dem Speichern. Der API-Schlüssel des Modellanbieters liegt nie im Browser.",
          "Der gemeinsame Kurs bleibt von deiner privaten Arbeit getrennt. Der Tutor kann freigegebenes Material lesen, aber nicht für alle umschreiben oder den Workspace anderer Lernender öffnen.",
        ],
        steps: [
          "Deine Frage und relevanter Kurskontext werden über das Backend an den Modellanbieter gesendet.",
          "Mit begrenzten Werkzeugen kann der Tutor Quellen lesen, Textstellen zeigen und persönliche Ergänzungen erstellen.",
          "Geprüfte Ergänzungen, der jüngste Gesprächsverlauf und Lernstand werden zum späteren Fortsetzen gespeichert.",
        ],
      },
      {
        id: "limits",
        title: "Was das Tool aussagen kann – und was nicht",
        paragraphs: [
          "Auch eine flüssige Erklärung kann falsch sein. Öffne die Quellen, hinterfrage unklare Schritte und melde Probleme über Feedback. Quellenprüfungen und die Freigabe durch Lehrende helfen, garantieren aber nicht jede Erklärung oder Bewertung.",
          "Kursanalysen zeigen Lernsignale aus dem Kurs, keine gewöhnlichen privaten Chats oder persönlichen Canvases. Antworten mit Hilfe und selbstständige Versuche bedeuten Unterschiedliches. Diese Signale sind keine Hochschulnote und kein Nachweis langfristigen Behaltens.",
          "Das Lehrkonzept orientiert sich an Lernforschung. Die eigene Lernwirksamkeit von LecturePilot muss noch untersucht werden.",
        ],
      },
    ],
  },
};
