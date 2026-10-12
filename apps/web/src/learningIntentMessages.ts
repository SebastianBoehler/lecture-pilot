export const learningIntentMessages = {
  en: {
    "builder.intent.reviewImplementation":
      "Your learning goals are already approved. Review how this canvas teaches them, then approve it for publication. To change the goals, return to Learning plan and generate a new draft.",
    "builder.intent.title": "Learning goals",
    "builder.intent.empty":
      "Propose source-backed goals for professor review. Practice tasks are developed after approval.",
    "builder.intent.generate": "Propose learning goals",
    "builder.intent.generating": "Proposing learning goals...",
    "builder.intent.help":
      "Decide what students should learn. AI develops and checks the teaching, practice and hints; you review the canvas before publication.",
    "builder.intent.approve": "Approve learning goals",
    "builder.intent.approved": "Learning goals approved",
    "builder.intent.approveAll": "Approve all {count} open learning plans",
    "builder.intent.finding":
      "Source check: the materials may not fully support this goal. {reason} Edit or remove it, or approve it as is.",
    "builder.intent.objectiveDerived":
      "The lecture objective is the list of these learning goals and updates automatically.",
    "builder.intent.details": "Inspect generated practice and support",
    "builder.intent.fixed": "Keep these tasks and rubric fixed",
    "builder.intent.fixedHelp":
      "Selected targets remain professor-owned in full. AI may repair other generated tasks while preserving every learning goal and constraint.",
    "builder.intent.convert": "Review learning goals instead",
    "builder.intent.conversion":
      "This plan was approved in full. Switching keeps the learning goals and constraints protected, but lets AI revise unselected tasks, rubrics and hints in unpublished drafts. The existing approval is retained in history; published material stays unchanged.",
    "builder.intent.confirmConversion": "I approve this change in responsibility",
    "builder.intent.repair":
      "AI will check and repair the teaching implementation during generation. Goal approval does not certify these generated details.",
    "builder.intent.goalTitle": "Learning goal title: {target}",
    "builder.intent.deleteGoal": "Delete learning goal: {target}",
    "builder.intent.minimumGoal":
      "Keep at least one learning goal. You can overwrite its title and outcome.",
    "builder.intent.edit": "Edit learning goals",
    "builder.intent.refresh": "Propose new learning goals",
  },
  de: {
    "builder.intent.reviewImplementation":
      "Die Lernziele sind bereits freigegeben. Prüfen Sie ihre Umsetzung in diesem Canvas und geben Sie ihn zur Veröffentlichung frei. Für Änderungen an den Lernzielen gehen Sie zum Lernplan zurück und erstellen einen neuen Entwurf.",
    "builder.intent.title": "Lernziele",
    "builder.intent.empty":
      "Lassen Sie quellenbasierte Lernziele zur Prüfung vorschlagen. Übungsaufgaben entstehen nach der Freigabe.",
    "builder.intent.generate": "Lernziele vorschlagen",
    "builder.intent.generating": "Lernziele werden vorgeschlagen...",
    "builder.intent.help":
      "Entscheiden Sie, was Studierende lernen sollen. Die KI entwickelt und prüft Erklärungen, Aufgaben und Hilfen. Vor der Veröffentlichung prüfen Sie den Canvas.",
    "builder.intent.approve": "Lernziele freigeben",
    "builder.intent.approved": "Lernziele freigegeben",
    "builder.intent.approveAll": "Alle {count} offenen Lernpläne freigeben",
    "builder.intent.finding":
      "Quellenprüfung: Die Materialien stützen dieses Ziel möglicherweise nicht vollständig. {reason} Sie können es bearbeiten, entfernen oder so freigeben.",
    "builder.intent.objectiveDerived":
      "Das Vorlesungsziel ist die Liste dieser Lernziele und wird automatisch aktualisiert.",
    "builder.intent.details": "Generierte Aufgaben und Hilfen ansehen",
    "builder.intent.fixed": "Diese Aufgaben und Bewertungskriterien festschreiben",
    "builder.intent.fixedHelp":
      "Ausgewählte Ziele bleiben mit allen Aufgabendetails unter Ihrer Kontrolle. Andere generierte Aufgaben darf die KI bei unveränderten Lernzielen und Rahmenbedingungen korrigieren.",
    "builder.intent.convert": "Stattdessen Lernziele prüfen",
    "builder.intent.conversion":
      "Dieser Plan wurde vollständig freigegeben. Beim Wechsel bleiben Lernziele und Rahmenbedingungen geschützt. Nicht ausgewählte Aufgaben, Kriterien und Hilfen darf die KI in unveröffentlichten Entwürfen ändern. Die bisherige Freigabe bleibt im Verlauf erhalten; veröffentlichte Inhalte bleiben unverändert.",
    "builder.intent.confirmConversion": "Ich stimme dieser Änderung der Zuständigkeit zu",
    "builder.intent.repair":
      "Die KI prüft und korrigiert die Umsetzung bei der Generierung. Die Freigabe der Lernziele bestätigt diese generierten Details nicht.",
    "builder.intent.goalTitle": "Titel des Lernziels: {target}",
    "builder.intent.deleteGoal": "Lernziel löschen: {target}",
    "builder.intent.minimumGoal":
      "Mindestens ein Lernziel ist erforderlich. Titel und Lernergebnis können überschrieben werden.",
    "builder.intent.edit": "Lernziele bearbeiten",
    "builder.intent.refresh": "Neue Lernziele vorschlagen",
  },
} as const;
