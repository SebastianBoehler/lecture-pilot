# LecturePilot changelog

A product-level history of improvements for students and lecturers. Technical details remain in the commit history.

[View all GitHub Releases](https://github.com/SebastianBoehler/lecture-pilot/releases)

## [0.2.1](https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.2.1) — Safer course generation and recovery

Released 2026-07-20

Lecture ordering, LaTeX slides, generation progress, and failed canvas drafts are now easier to review and recover.

### What changed

- **Targeted AI repair** _(From feedback)_ — When one generated block fails validation, Retry repairs only that block or section, checks the complete draft again, and preserves unchanged content.
- **Broader LaTeX slide support** — LecturePilot now handles more real-world TeX layouts, including graphics with decimal-style filenames, while keeping compilation isolated.
- **Review lecture order before generation** _(From feedback)_ — Detected lectures follow their source filenames and can be reordered with drag handles or accessible move controls before applying the schedule.
- **Clear generation timing** _(From feedback)_ — The course builder estimates the duration and makes clear that generation continues on the server, so lecturers can leave and return later.

### Deutsch

**Sicherere Kurserstellung und Wiederherstellung**

Vorlesungsreihenfolge, LaTeX-Folien, Generierungsfortschritt und fehlgeschlagene Canvas-Entwürfe lassen sich jetzt leichter prüfen und wiederherstellen.

- **Gezielte KI-Reparatur** _(Aus Feedback)_ — Wenn ein generierter Block die Prüfung nicht besteht, repariert Wiederholen nur diesen Block oder Abschnitt, prüft den vollständigen Entwurf erneut und erhält unveränderte Inhalte.
- **Breitere Unterstützung für LaTeX-Folien** — LecturePilot verarbeitet jetzt mehr praxisnahe TeX-Strukturen, einschließlich Grafiken mit dezimalartigen Dateinamen, und hält die Kompilierung weiterhin isoliert.
- **Vorlesungsreihenfolge vor der Generierung prüfen** _(Aus Feedback)_ — Erkannte Vorlesungen folgen ihren Quelldateinamen und können vor dem Übernehmen des Zeitplans per Ziehgriff oder zugänglichen Verschiebeschaltflächen sortiert werden.
- **Klare Generierungsdauer** _(Aus Feedback)_ — Die Kurserstellung schätzt die Dauer und weist darauf hin, dass die Generierung auf dem Server weiterläuft, sodass Lehrende später zurückkehren können.

## [0.2.0](https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.2.0) — A complete pilot flow for students and lecturers

Released 2026-07-13

University sign-in, course maintenance, adaptive tutoring, and lecturer previews now work as one connected experience.

### What changed

- **University accounts and courses** — Students and lecturers sign in through Alma. LecturePilot uses their verified role, preloads profile details, and shows courses from Alma and ILIAS with their source.
- **Courses can grow during the semester** _(From feedback)_ — Lecturers can add new lecture material to an existing course, review detected lectures, and remove unwanted lectures before generation without rebuilding the course.
- **A private student preview for lecturers** — Lecturers can open published lectures as a student, use the tutor, and test progress and memory without accessing or changing a real student's workspace.
- **More adaptive study guidance** — A short calibration, one recommended next study step, evidence-based tutor guidance, and transparent memory controls keep the experience focused on demonstrated understanding.
- **Clearer lecturer oversight** — Course performance and model usage are visible in dedicated views while private learner chats and workspaces remain separated.

### Deutsch

**Ein vollständiger Pilotablauf für Studierende und Lehrende**

Uni-Anmeldung, Kurspflege, adaptives Tutoring und die Vorschau für Lehrende greifen jetzt als ein zusammenhängender Ablauf ineinander.

- **Uni-Konten und Kurse** — Studierende und Lehrende melden sich über Alma an. LecturePilot übernimmt die verifizierte Rolle und Profildaten und zeigt Kurse aus Alma und ILIAS mit ihrer Quelle.
- **Kurse können im Semester weiterwachsen** _(Aus Feedback)_ — Lehrende können neue Unterlagen zu einem bestehenden Kurs ergänzen, erkannte Vorlesungen prüfen und unerwünschte Vorlesungen vor der Generierung entfernen, ohne den Kurs neu aufzubauen.
- **Eine private Studierendenansicht für Lehrende** — Lehrende können veröffentlichte Vorlesungen wie Studierende öffnen und Tutor, Fortschritt und Erinnerungen testen, ohne auf den Arbeitsbereich echter Studierender zuzugreifen.
- **Adaptivere Lernbegleitung** — Eine kurze Kalibrierung, ein empfohlener nächster Lernschritt, evidenzbasierte Tutor-Hinweise und transparente Erinnerungskontrollen richten das Lernen am gezeigten Verständnis aus.
- **Besserer Überblick für Lehrende** — Kursfortschritt und Modellnutzung sind in eigenen Ansichten sichtbar, während private Chats und Arbeitsbereiche der Studierenden getrennt bleiben.

## [0.1.0](https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.1.0) — The first LecturePilot foundation

Released 2026-07-08

The initial pilot connected course material, structured learning canvases, and a source-aware AI tutor.

### What changed

- **Course-aware learning workspaces** — Lecture material becomes a structured canvas with explanations, original slides, quizzes, checkpoints, and source references.
- **A tutor that works inside the course** — The tutor can explain, highlight, check understanding, and add learner-owned notes while staying inside authorized lecture material.
- **Tools for lecturers** — Lecturers can upload material, review generated lectures, publish selected content, and inspect course-level learning signals.
- **Private learner state by design** — Course sources, professor-approved canvases, and each learner's progress, notes, and memory are stored as separate layers.

### Deutsch

**Das erste LecturePilot-Fundament**

Der erste Pilot verband Kursmaterialien, strukturierte Lernansichten und einen quellenbasierten KI-Tutor.

- **Kursbezogene Lernarbeitsbereiche** — Vorlesungsmaterial wird zu einer strukturierten Lernansicht mit Erklärungen, Originalfolien, Quizzen, Checkpoints und Quellenangaben.
- **Ein Tutor, der im Kurs arbeitet** — Der Tutor kann erklären, hervorheben, Verständnis prüfen und eigene Lernnotizen ergänzen, bleibt dabei aber innerhalb freigegebener Vorlesungsmaterialien.
- **Werkzeuge für Lehrende** — Lehrende können Materialien hochladen, generierte Vorlesungen prüfen, ausgewählte Inhalte veröffentlichen und Lernsignale auf Kursebene einsehen.
- **Private Lernstände von Grund auf** — Kursquellen, von Lehrenden freigegebene Lernansichten sowie Fortschritt, Notizen und Erinnerungen einzelner Lernender werden als getrennte Ebenen gespeichert.
