import type { InfoArticleContent } from "./infoArticleTypes";

export const learningGuideContent: Record<"en" | "de", InfoArticleContent> = {
  en: {
    title: "Learning how to learn",
    intro:
      "Use LecturePilot to do more of the thinking yourself. A useful session ends with something you can explain or solve without the tutor—not just an answer that looks convincing.",
    sections: [
      {
        id: "prediction",
        title: "Make a prediction before learning",
        paragraphs: [
          "When a lecture offers a Before you begin card, make a brief guess and explain why. It is fine to be wrong or skip. After reading the explanation, compare it with your first idea or ask the tutor to revisit it.",
        ],
        detail:
          "Your first prediction is saved privately for that lecture version. It is not graded and does not count as independent evidence.",
      },
      {
        id: "attempt",
        title: "Start with your own attempt",
        paragraphs: [
          "Before reopening the slides, write down what you remember or try one representative problem. Then compare with the source. Recognizing an explanation is easier than producing it yourself; retrieval practice helps you notice that difference.",
        ],
        example:
          "Open a checkpoint and write your reasoning before asking for help. An incomplete attempt gives the tutor something concrete to respond to.",
      },
      {
        id: "help",
        title: "Ask for the next useful hint",
        paragraphs: [
          "Tell the tutor where your reasoning stops. If the prerequisites are unfamiliar, start with a worked example, then cover the next step and try it yourself. Help should make the next attempt possible.",
        ],
        example:
          "“I got as far as this equation. Why is the next step valid? Give me a hint before the full solution.”",
        detail:
          "A correct answer after a hint is supported work. It is useful progress, but it is different from doing the task independently. The app records assistance for its structured learning checks.",
      },
      {
        id: "explain",
        title: "Explain it back",
        paragraphs: [
          "Put the idea in your own words and give a small example. A diagram can help with geometry; a derivation may help with a formula. Choose a representation that fits the problem rather than assigning yourself a fixed learning type.",
        ],
        example:
          "“Here is my explanation of overfitting. Which part is missing?” Ask for an annotation at the confusing passage so you can revisit it later.",
      },
      {
        id: "independent",
        title: "Try a fresh problem without help",
        paragraphs: [
          "After working through feedback, attempt a new problem. Repeating a solution you just saw can feel like understanding. Changing the example is a better opportunity to check whether you can use the idea.",
        ],
        example:
          "Use the fresh independent task offered after supported work. Teaching, notes and chat are hidden during that attempt. Answer before returning to the explanation.",
        detail:
          "The result is evidence about this attempt, not proof that the topic will remain secure next month. Fresh tasks depend on the reviewed task bank; exhaustion is shown explicitly.",
      },
      {
        id: "return",
        title: "Return after a gap",
        paragraphs: [
          "Revisit the topic after some time has passed, and mix it with earlier topics. A brief recall check the next day and another later in the week can be a practical starting point; adjust to what you can retrieve.",
        ],
        example:
          "Choose one earlier lecture at your next visit. Explain its central idea without notes, then open the source to repair gaps.",
        detail:
          "This is study advice, not an automatic spaced-repetition schedule promised by the app. Useful spacing depends on the material and when you need to remember it.",
      },
      {
        id: "exam",
        title: "Use an exam as an attempt, not a reading list",
        paragraphs: [
          "For exam preparation, work through the questions before looking at the separate solutions. Explain why your answer differs and revisit the relevant learning goal. Practice-exam submissions are saved for your own review; there is no server-side grading.",
        ],
        example:
          "Generate a practice exam, answer under your chosen exam conditions, and only then open the solution sheet. Bring a specific mistake back to the tutor.",
      },
      {
        id: "routine",
        title: "A small routine you can repeat",
        paragraphs: [
          "Start with one concept and one achievable next step. You do not need to finish the whole lecture in one sitting.",
        ],
        steps: [
          "Recall: write what you already know without opening notes.",
          "Attempt: solve, derive, explain or sketch one problem.",
          "Check: inspect the source and ask for targeted feedback.",
          "Retry: use a fresh task without help, then plan when to return.",
        ],
      },
      {
        id: "research",
        title: "Research behind the advice",
        paragraphs: [
          "These recommendations draw on retrieval practice, constructive alignment, feedback and distributed practice. They inform the design; they are not studies showing that LecturePilot itself improves learning. The links below provide starting points for reading further.",
        ],
      },
    ],
  },
  de: {
    title: "Lernen lernen",
    intro:
      "Nutze LecturePilot, um selbst mehr zu durchdenken. Am Ende einer hilfreichen Sitzung kannst du etwas ohne Tutor erklären oder lösen – nicht nur eine überzeugend klingende Antwort lesen.",
    sections: [
      {
        id: "prediction",
        title: "Stelle vor dem Lernen eine Vermutung auf",
        paragraphs: [
          "Wenn eine Vorlesung die Karte Bevor du beginnst enthält, notiere eine kurze Vermutung und begründe sie. Du darfst falsch liegen oder überspringen. Vergleiche die Erklärung danach mit deiner ersten Idee oder sprich den Tutor darauf an.",
        ],
        detail:
          "Deine erste Vermutung bleibt privat und ist an diese Vorlesungsversion gebunden. Sie wird nicht bewertet und zählt nicht als eigenständiger Leistungsnachweis.",
      },
      {
        id: "attempt",
        title: "Beginne mit deinem eigenen Versuch",
        paragraphs: [
          "Schreibe vor dem erneuten Öffnen der Folien auf, woran du dich erinnerst, oder versuche eine typische Aufgabe. Vergleiche erst danach mit der Quelle. Eine Erklärung wiederzuerkennen ist leichter, als sie selbst zu formulieren. Aktives Abrufen macht diesen Unterschied sichtbar.",
        ],
        example:
          "Öffne einen Checkpoint und schreibe deinen Lösungsweg, bevor du Hilfe anforderst. Auch ein unvollständiger Versuch gibt dem Tutor einen konkreten Ansatzpunkt.",
      },
      {
        id: "help",
        title: "Bitte um den nächsten hilfreichen Hinweis",
        paragraphs: [
          "Sag dem Tutor, an welcher Stelle dein Gedankengang endet. Fehlen dir Grundlagen, beginne mit einem ausgearbeiteten Beispiel. Decke danach den nächsten Schritt ab und versuche ihn selbst. Hilfe soll den nächsten eigenen Versuch ermöglichen.",
        ],
        example:
          "„Bis zu dieser Gleichung komme ich. Warum ist der nächste Schritt erlaubt? Gib mir erst einen Hinweis statt der ganzen Lösung.“",
        detail:
          "Eine richtige Antwort nach einem Hinweis ist unterstützte Arbeit. Das ist sinnvoller Fortschritt, aber etwas anderes als eine selbstständig gelöste Aufgabe. Bei strukturierten Lernchecks zeichnet die App erhaltene Unterstützung auf.",
      },
      {
        id: "explain",
        title: "Erkläre es zurück",
        paragraphs: [
          "Formuliere die Idee in eigenen Worten und nenne ein kleines Beispiel. Eine Skizze kann bei Geometrie helfen, eine Herleitung bei einer Formel. Wähle eine Darstellung passend zur Aufgabe, statt dich einem festen Lerntyp zuzuordnen.",
        ],
        example:
          "„So würde ich Overfitting erklären. Was fehlt noch?“ Bitte um eine Annotation an der unklaren Textstelle, um später darauf zurückzukommen.",
      },
      {
        id: "independent",
        title: "Versuche eine neue Aufgabe ohne Hilfe",
        paragraphs: [
          "Versuche nach dem Feedback ein neues Problem. Eine gerade gesehene Lösung zu wiederholen kann sich wie Verstehen anfühlen. Ein anderes Beispiel gibt dir eher Gelegenheit zu prüfen, ob du die Idee anwenden kannst.",
        ],
        example:
          "Nutze die neue selbstständige Aufgabe nach unterstützter Arbeit. Während des Versuchs sind Erklärungen, Notizen und Chat ausgeblendet. Antworte, bevor du wieder zur Erklärung gehst.",
        detail:
          "Das Ergebnis sagt etwas über diesen Versuch aus, nicht darüber, ob das Thema nächsten Monat noch sitzt. Neue Aufgaben hängen vom geprüften Aufgabenvorrat ab; ist er aufgebraucht, wird das angezeigt.",
      },
      {
        id: "return",
        title: "Komm mit Abstand darauf zurück",
        paragraphs: [
          "Greife ein Thema nach einer Pause wieder auf und mische es mit älteren Themen. Ein kurzer Abrufversuch am nächsten Tag und ein weiterer später in der Woche können ein Ausgangspunkt sein. Passe den Abstand daran an, was du noch abrufen kannst.",
        ],
        example:
          "Wähle beim nächsten Besuch eine ältere Vorlesung. Erkläre die zentrale Idee ohne Notizen und öffne danach die Quelle, um Lücken zu schließen.",
        detail:
          "Das ist eine Lernempfehlung, kein Versprechen eines automatischen Wiederholungsplans in der App. Sinnvolle Abstände hängen vom Stoff und deinem Zeithorizont ab.",
      },
      {
        id: "exam",
        title: "Nutze eine Klausur zum Lösen, nicht nur zum Lesen",
        paragraphs: [
          "Bearbeite zur Prüfungsvorbereitung zuerst die Fragen und öffne erst danach die getrennten Lösungen. Erkläre Abweichungen und kehre zum entsprechenden Lernziel zurück. Übungsklausurabgaben werden zur eigenen Nachbereitung gespeichert; eine serverseitige Benotung gibt es nicht.",
        ],
        example:
          "Erzeuge eine Übungsklausur, bearbeite sie unter selbst gewählten Prüfungsbedingungen und öffne erst dann das Lösungsblatt. Besprich einen konkreten Fehler mit dem Tutor.",
      },
      {
        id: "routine",
        title: "Eine kleine Routine zum Wiederholen",
        paragraphs: [
          "Beginne mit einem Konzept und einem machbaren nächsten Schritt. Du musst nicht die ganze Vorlesung in einer Sitzung abschließen.",
        ],
        steps: [
          "Abrufen: Schreibe ohne Notizen auf, was du weißt.",
          "Versuchen: Löse, leite her, erkläre oder skizziere ein Problem.",
          "Prüfen: Sieh in die Quelle und frage gezielt nach Feedback.",
          "Erneut versuchen: Löse eine neue Aufgabe ohne Hilfe und plane die nächste Wiederholung.",
        ],
      },
      {
        id: "research",
        title: "Forschung hinter den Empfehlungen",
        paragraphs: [
          "Diese Empfehlungen greifen Forschung zu aktivem Abrufen, der Abstimmung von Lernzielen und Aufgaben, Feedback und verteiltem Üben auf. Sie begründen das Design; sie sind keine Studien zur Lernwirksamkeit von LecturePilot selbst. Die folgenden Links sind Ausgangspunkte zum Weiterlesen.",
        ],
      },
    ],
  },
};
