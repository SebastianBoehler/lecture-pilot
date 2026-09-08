import type { InfoArticleContent } from "./infoArticleTypes";

export const privacyContent: Record<"en" | "de", InfoArticleContent> = {
  en: {
    title: "Privacy and your data",
    intro:
      "What LecturePilot saves, what reaches an AI provider, and what other people can see. This describes the university pilot as checked on 7 September 2026; institutional details still awaiting confirmation are listed below.",
    sections: [
      {
        id: "account",
        title: "Signing in and course access",
        paragraphs: [
          "Your university sign-in is handled by the LecturePilot service to load your account role, courses and access rights. Your password is not stored in the web app or sent to an AI model provider. University authentication services process the sign-in.",
          "Being able to manage a course does not mean it is published to students. Access checks also apply to source files, learner workspaces and lecture availability.",
        ],
      },
      {
        id: "saved",
        title: "What is saved?",
        paragraphs: [
          "Course workspaces contain uploaded materials, processed sources, source assignments, learning plans, generated drafts and published lectures. After source confirmation, unused uploads can be removed while referenced sources and required dependencies are retained. Private authoring records may contain source excerpts and generated drafts.",
          "Your private workspace can contain attendance mode, progress, checkpoint and exam-check attempts, recent tutor messages, annotations, personal sections, generated images, memories, practice exams and saved submissions. These support continuation and personalized guidance.",
          "Optional imported exam-protocol archives and extracted text are stored privately within your course workspace until deleted. Their login credentials are request-only. Practice-exam answer drafts stay in the browser tab until you explicitly submit them.",
        ],
      },
      {
        id: "provider",
        title: "What reaches an AI provider?",
        paragraphs: [
          "The current university deployment uses OpenAI for tutor model requests. Requests pass through the backend and may include your question, relevant source excerpts, canvas content, up to eight recent learner and tutor messages from this lecture, learning state, saved preferences or memories, and relevant saved practice history. Course creation also sends relevant teaching material and approved learning goals for generation and review.",
          "Image requests can include the prompt and educational context. University hosting does not mean inference stays on the university server. Provider processing and retention are separate from LecturePilot storage; this notice does not promise zero provider retention. Consult the provider data controls linked below.",
          "The onboarding video is served by LecturePilot. Playing an embedded external course video or following an external research link contacts that external service.",
        ],
      },
      {
        id: "browser-agents",
        title: "External browser agents",
        paragraphs: [
          "While you are signed in as a student, supporting browser agents can use WebMCP tools to read your authorized course and lecture metadata, passed lectures and recorded gate evidence. They can open courses and lectures and change the interface theme or language. Your chosen agent may process the returned information under its own data policies.",
          "These tools do not expose answers, assessment prompts, private notes or tutor conversations, and cannot submit learning work or change progress. Signing out removes the tools. This tool boundary does not prevent a general browser agent from reading or operating other visible parts of the page.",
        ],
      },
      {
        id: "memory",
        title: "What does the tutor remember?",
        paragraphs: [
          "Recent conversation belongs to the lecture. Course memory records course-specific learning observations. Cross-course memory and preferences can carry useful context, such as a preference for step-by-step explanations, into another course. Official materials and permissions remain course-specific.",
          "You can inspect and remove saved preferences and memory in your profile. Deleting a preference does not also delete every earlier message or generated file where you mentioned it.",
        ],
      },
      {
        id: "visibility",
        title: "Who can see my work?",
        paragraphs: [
          "Other students cannot open your private learner workspace. Course staff do not see ordinary private chat messages or your personal canvas in course analytics. Private annotations are not public comments or questions to your lecturer. Before you begin predictions are also private: the question, first answer (or skip), lecture version and save time are stored in your lecture workspace. Current predictions may be sent to the model as context for tutor responses; they are not graded or included in professor analytics. They are removed with a course-workspace reset or account deletion.",
          "Professor analytics contain course-level learning signals and usage information. Versioned outcome records include attempt kind and index, assistance before the attempt, planned and observed delay, and the associated publication and learning-map revisions. They do not contain answer text or ordinary tutor messages. Professor preview activity is excluded, and cohort percentages are hidden when fewer than five learners contribute.",
          "Authorized service operators can administer stored data and backups. Operational records include request status, timing, token usage and errors. The current deployment is configured for metadata-only tracing; technical administration is separate from the professor analytics interface.",
          "These signals do not establish learning efficacy or enrollment in a research study. Any additional research collection needs its own participant information and applicable institutional review.",
        ],
      },
      {
        id: "delete",
        title: "What can I delete?",
        paragraphs: [
          "You can delete annotations and saved practice-exam submissions using their controls, delete imported exam sources, and remove saved memory or preferences in your profile.",
          "A course workspace reset lets you choose which categories to clear. Read the selected options: resetting personal canvas content is different from clearing progress, course memory or practice exams. It does not rewrite the professor-approved course or automatically erase cross-course memory. Course managers can delete course workspaces.",
          "Application deletion should not be read as immediate removal from every backup or provider record. Backup expiry and the institutional retention schedule remain to be confirmed.",
        ],
      },
      {
        id: "institution",
        title: "University pilot: details still to be confirmed",
        paragraphs: [
          "The application and its persisted workspaces run on University of Tübingen infrastructure at lecturepilot.cs.uni-tuebingen.de. Model processing is described separately above.",
          "The designated data controller and privacy contact, applicable legal basis, complete processor and transfer information, retention periods, backup expiry and formal procedure for exercising data rights still require institutional confirmation. This technical description does not replace those details. For pilot questions, contact your course staff or use the application’s Feedback function; a formal privacy contact is not yet designated here.",
        ],
      },
    ],
  },
  de: {
    title: "Datenschutz und deine Daten",
    intro:
      "Was LecturePilot speichert, was an einen KI-Anbieter gesendet wird und was andere sehen können. Stand des Hochschulpiloten: 7. September 2026. Noch institutionell zu bestätigende Angaben stehen unten.",
    sections: [
      {
        id: "account",
        title: "Anmeldung und Kurszugang",
        paragraphs: [
          "Die Anmeldung wird vom LecturePilot-Dienst verarbeitet, um Kontorolle, Kurse und Zugangsrechte zu laden. Dein Passwort wird nicht in der Web-App gespeichert oder an einen KI-Modellanbieter gesendet. Die Hochschuldienste verarbeiten die Authentifizierung.",
          "Ein verwaltbarer Kurs ist nicht automatisch für Studierende veröffentlicht. Zugangsprüfungen gelten auch für Quellen, Lernworkspaces und verfügbare Vorlesungen.",
        ],
      },
      {
        id: "saved",
        title: "Was wird gespeichert?",
        paragraphs: [
          "Kursworkspaces enthalten hochgeladene Materialien, verarbeitete Quellen, Quellenzuordnungen, Lernpläne, erzeugte Entwürfe und veröffentlichte Vorlesungen. Nach Bestätigung der Quellen können ungenutzte Uploads entfernt werden; referenzierte Quellen und benötigte Abhängigkeiten bleiben erhalten. Private Erstellungsprotokolle können Quellenauszüge und erzeugte Entwürfe enthalten.",
          "Dein privater Workspace kann Anwesenheitsmodus, Fortschritt, Checkpoint- und Prüfungscheckversuche, jüngste Tutornachrichten, Annotationen, persönliche Abschnitte, erzeugte Bilder, Erinnerungen, Übungsklausuren und gespeicherte Abgaben enthalten. Damit kannst du später fortsetzen und passende Unterstützung erhalten.",
          "Optional importierte Prüfungsprotokollarchive und extrahierte Texte bleiben bis zum Löschen privat in deinem Kursworkspace. Ihre Zugangsdaten werden nur für die Anfrage verwendet. Antwortentwürfe für Übungsklausuren bleiben bis zur ausdrücklichen Abgabe im Browser-Tab.",
        ],
      },
      {
        id: "provider",
        title: "Was erhält ein KI-Anbieter?",
        paragraphs: [
          "Die aktuelle Hochschulinstanz nutzt OpenAI für Tutor-Modellanfragen. Über das Backend können deine Frage, relevante Quellenauszüge, Canvas-Inhalte, bis zu acht jüngste Lernenden- und Tutornachrichten dieser Vorlesung, Lernstand, gespeicherte Vorlieben oder Erinnerungen und relevante gespeicherte Übungshistorie übermittelt werden. Auch bei der Kurserstellung werden relevante Lehrmaterialien und bestätigte Lernziele zur Generierung und Prüfung gesendet.",
          "Bildanfragen können den Prompt und den didaktischen Kontext enthalten. Hochschulhosting bedeutet nicht, dass die Modellverarbeitung auf dem Hochschulserver bleibt. Verarbeitung und Aufbewahrung beim Anbieter sind von LecturePilot getrennt; dieser Hinweis verspricht keine aufbewahrungsfreie Verarbeitung. Die Informationen des Anbieters sind unten verlinkt.",
          "Das Einführungsvideo wird von LecturePilot ausgeliefert. Beim Abspielen eingebetteter externer Kursvideos oder Öffnen externer Forschungslinks wird der jeweilige externe Dienst kontaktiert.",
        ],
      },
      {
        id: "browser-agents",
        title: "Externe Browser-Agenten",
        paragraphs: [
          "Solange du als Student angemeldet bist, können unterstützte Browser-Agenten über WebMCP deine berechtigten Kurs- und Vorlesungsmetadaten, bestandene Vorlesungen und gespeicherte Lernnachweise lesen. Sie können Kurse und Vorlesungen öffnen sowie Sprache und Darstellung der Oberfläche ändern. Dein gewählter Agent kann diese Informationen nach seinen eigenen Datenschutzregeln verarbeiten.",
          "Diese Werkzeuge geben keine Antworten, Prüfungsaufgaben, privaten Notizen oder Tutor-Gespräche weiter und können keine Lernarbeit abgeben oder Fortschritt verändern. Beim Abmelden werden sie entfernt. Diese Werkzeuggrenze verhindert nicht, dass ein allgemeiner Browser-Agent andere sichtbare Seitenbereiche liest oder bedient.",
        ],
      },
      {
        id: "memory",
        title: "Was merkt sich der Tutor?",
        paragraphs: [
          "Der jüngste Gesprächsverlauf gehört zur Vorlesung. Kurserinnerungen enthalten kursbezogene Lernbeobachtungen. Kursübergreifende Erinnerungen und Vorlieben können hilfreichen Kontext – etwa den Wunsch nach schrittweisen Erklärungen – in andere Kurse übernehmen. Offizielle Materialien und Berechtigungen bleiben kursbezogen.",
          "Gespeicherte Vorlieben und Erinnerungen kannst du im Profil ansehen und entfernen. Das Löschen einer Vorliebe entfernt nicht zugleich jede frühere Nachricht oder erzeugte Datei, in der sie vorkam.",
        ],
      },
      {
        id: "visibility",
        title: "Wer kann meine Arbeit sehen?",
        paragraphs: [
          "Andere Studierende können deinen privaten Lernworkspace nicht öffnen. Lehrende sehen in Kursanalysen keine gewöhnlichen privaten Chatnachrichten oder persönlichen Canvases. Private Annotationen sind keine öffentlichen Kommentare oder Fragen an Lehrende. Auch Vermutungen aus Bevor du beginnst bleiben privat: Frage, erste Antwort (oder Überspringen), Vorlesungsversion und Speicherzeit liegen im Vorlesungsworkspace. Aktuelle Vermutungen können dem Modell als Kontext für Tutorantworten übermittelt werden. Sie werden nicht bewertet oder in Lehrendenanalysen aufgenommen. Beim Zurücksetzen des Kursworkspaces oder Löschen des Kontos werden sie entfernt.",
          "Lehrendenanalysen enthalten kursweite Lernsignale und Nutzungsinformationen. Versionierte Ergebnisdaten enthalten Versuchsart und -index, vorherige Unterstützung, geplante und beobachtete Verzögerung sowie die zugehörigen Veröffentlichungs- und Lernzielversionen. Antworttexte und gewöhnliche Tutornachrichten sind darin nicht enthalten. Vorschauaktivität von Lehrenden wird ausgeschlossen; Kohortenprozentwerte werden bei weniger als fünf beitragenden Lernenden ausgeblendet.",
          "Berechtigte Betreiber können gespeicherte Daten und Backups administrieren. Betriebsdaten umfassen Anfragestatus, Laufzeit, Tokenverbrauch und Fehler. Die aktuelle Instanz ist für Tracing mit Metadaten konfiguriert; technische Administration ist von der Lehrendenanalyse getrennt.",
          "Diese Signale belegen keine Lernwirksamkeit oder Teilnahme an einer Studie. Zusätzliche Forschungsdatenerhebung benötigt eigene Teilnahmeinformationen und die jeweils erforderliche institutionelle Prüfung.",
        ],
      },
      {
        id: "delete",
        title: "Was kann ich löschen?",
        paragraphs: [
          "Annotationen, gespeicherte Übungsklausurabgaben und importierte Prüfungsquellen kannst du über die jeweiligen Bedienelemente löschen. Gespeicherte Erinnerungen und Vorlieben entfernst du im Profil.",
          "Beim Zurücksetzen eines Kursworkspaces wählst du die zu löschenden Kategorien. Beachte die Auswahl: Persönliche Canvas-Inhalte, Fortschritt, Kurserinnerungen und Übungsklausuren sind unterschiedliche Bereiche. Der freigegebene Kurs wird dadurch nicht umgeschrieben, kursübergreifende Erinnerung nicht automatisch entfernt. Kursverantwortliche können Kursworkspaces löschen.",
          "Löschen in der Anwendung bedeutet nicht sofortiges Entfernen aus allen Backups oder Anbieteraufzeichnungen. Backup-Ablauf und institutionelle Aufbewahrungsfristen sind noch zu bestätigen.",
        ],
      },
      {
        id: "institution",
        title: "Hochschulpilot: noch zu bestätigende Angaben",
        paragraphs: [
          "Anwendung und gespeicherte Workspaces laufen auf Infrastruktur der Universität Tübingen unter lecturepilot.cs.uni-tuebingen.de. Die Modellverarbeitung ist oben getrennt beschrieben.",
          "Benannte datenschutzrechtlich verantwortliche Stelle und Kontakt, Rechtsgrundlage, vollständige Angaben zu Auftragsverarbeitung und Übermittlungen, Aufbewahrungsfristen, Backup-Ablauf und das formale Verfahren für Betroffenenrechte müssen institutionell bestätigt werden. Diese technische Beschreibung ersetzt diese Angaben nicht. Bei Fragen zum Piloten helfen Kursverantwortliche oder die Feedback-Funktion; ein formaler Datenschutzkontakt ist hier noch nicht benannt.",
        ],
      },
    ],
  },
};
