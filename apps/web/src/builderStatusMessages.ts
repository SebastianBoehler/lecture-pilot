/** Status lines the course builder shows after an action completes. */
export const builderStatusMessages = {
  en: {
    "builder.status.createdCourse":
      "Course workspace {course} ready. Upload materials to infer the lecture schedule.",
    "builder.status.createdLecture": "Course workspace {course}/{lecture} ready.",
    "builder.status.uploadedOne": "Uploaded {path} as {kind}.",
    "builder.status.uploadedMany": "Uploaded {count} materials into the source bundle.",
    "builder.status.ignoredOne": "Ignored 1 file: {names}.",
    "builder.status.ignoredMany": "Ignored {count} files: {names}.",
    "builder.status.ignoredMore": "{names}, and {count} more",
    "builder.status.scheduleApplied": "Lecture schedule applied with {count} dated lectures.",
    "builder.status.generatedOne": "Course-builder agent generated a source-grounded canvas draft.",
    "builder.status.generatedMany":
      "Course-builder agent generated {count} source-grounded lecture canvases.",
    "builder.status.videosFound": "Found {count} YouTube candidates.",
    "builder.status.videosSuggested":
      "Found {count} suggested YouTube candidates from {searches} searches.",
    "builder.status.videoRemoved": "Removed video from lecture {lecture}.",
    "builder.status.videoSavedOne": "Saved 1 approved video for lecture {lecture}.",
    "builder.status.videoSavedMany": "Saved {count} approved videos for lecture {lecture}.",
    "builder.status.publishedOne": "Tutor workspace published as version {version}.",
    "builder.status.publishedOneAt": "Tutor workspace published as version {version} at {when}.",
    "builder.status.publishedMany": "{count} tutor workspaces published for students.",
    "builder.status.publishedManyAt": "{count} tutor workspaces published for students at {when}.",
    "builder.status.routingRebuilt": "Source assignments rebuilt from the indexed course evidence.",
    "builder.status.routingConfirmed": "Source assignments confirmed for Canvas generation.",
  },
  de: {
    "builder.status.createdCourse":
      "Kursarbeitsbereich {course} ist bereit. Lade Materialien hoch, um den Vorlesungsplan abzuleiten.",
    "builder.status.createdLecture": "Kursarbeitsbereich {course}/{lecture} ist bereit.",
    "builder.status.uploadedOne": "{path} als {kind} hochgeladen.",
    "builder.status.uploadedMany": "{count} Materialien in das Quellenbündel hochgeladen.",
    "builder.status.ignoredOne": "1 Datei ignoriert: {names}.",
    "builder.status.ignoredMany": "{count} Dateien ignoriert: {names}.",
    "builder.status.ignoredMore": "{names} und {count} weitere",
    "builder.status.scheduleApplied":
      "Vorlesungsplan mit {count} datierten Vorlesungen übernommen.",
    "builder.status.generatedOne": "Ein quellenbasierter Canvas-Entwurf wurde erstellt.",
    "builder.status.generatedMany": "{count} quellenbasierte Vorlesungs-Canvases wurden erstellt.",
    "builder.status.videosFound": "{count} YouTube-Kandidaten gefunden.",
    "builder.status.videosSuggested":
      "{count} vorgeschlagene YouTube-Kandidaten aus {searches} Suchen gefunden.",
    "builder.status.videoRemoved": "Video aus Vorlesung {lecture} entfernt.",
    "builder.status.videoSavedOne": "1 freigegebenes Video für Vorlesung {lecture} gespeichert.",
    "builder.status.videoSavedMany":
      "{count} freigegebene Videos für Vorlesung {lecture} gespeichert.",
    "builder.status.publishedOne": "Tutor-Arbeitsbereich als Version {version} veröffentlicht.",
    "builder.status.publishedOneAt":
      "Tutor-Arbeitsbereich am {when} als Version {version} veröffentlicht.",
    "builder.status.publishedMany": "{count} Tutor-Arbeitsbereiche für Studierende veröffentlicht.",
    "builder.status.publishedManyAt":
      "{count} Tutor-Arbeitsbereiche am {when} für Studierende veröffentlicht.",
    "builder.status.routingRebuilt":
      "Quellenzuordnungen aus den indexierten Kursquellen neu erstellt.",
    "builder.status.routingConfirmed": "Quellenzuordnungen für die Canvas-Erstellung bestätigt.",
  },
} as const;
