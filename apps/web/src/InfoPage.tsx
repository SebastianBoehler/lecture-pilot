import type { InfoPageKind } from "./types";

export function InfoPage({ kind, onBack }: { kind: InfoPageKind; onBack: () => void }) {
  const content = INFO_CONTENT[kind];
  return (
    <main className="info-page">
      <button className="ghost-button info-back" type="button" onClick={onBack}>Back</button>
      <section className="info-hero">
        <p className="section-label">{content.label}</p>
        <h1>{content.title}</h1>
        <p>{content.intro}</p>
      </section>
      <div className="info-grid">
        {content.sections.map((section) => (
          <section className="info-section" key={section.title}>
            <h2>{section.title}</h2>
            <ul>
              {section.items.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}

type InfoContent = {
  label: string;
  title: string;
  intro: string;
  sections: Array<{ title: string; items: string[] }>;
};

const INFO_CONTENT: Record<InfoPageKind, InfoContent> = {
  "how-it-works": {
    label: "Plain-language project overview",
    title: "How LecturePilot works",
    intro: "LecturePilot turns approved course material into a guided learning workspace. The tutor can read the current lecture canvas, add learner-owned notes, ask checks, and remember study preferences when you allow it.",
    sections: [
      {
        title: "What the agent sees",
        items: [
          "Only the course, lecture, canvas, attendance mode, and chat messages needed for the current action.",
          "Professor-uploaded material after it has been added to the course workspace.",
          "Your learner workspace for the selected course, including generated notes, images, quiz attempts, and progress.",
        ],
      },
      {
        title: "What the agent can do",
        items: [
          "Read course sections and explain them step by step.",
          "Create or update learner-owned canvas sections without changing professor source files.",
          "Generate practice questions, readiness feedback, and visual explanations when configured.",
        ],
      },
      {
        title: "What stays separated",
        items: [
          "Official course material is separate from personal learner notes.",
          "Course-specific progress is separate from cross-course learning preferences.",
          "Professor analytics use learning signals, not raw private chat transcripts.",
        ],
      },
    ],
  },
  privacy: {
    label: "Datenschutz overview",
    title: "What data is processed",
    intro: "This pilot page explains the intended data flow in simple terms. A production deployment still needs the university-specific legal notice, controller details, retention periods, and contact information.",
    sections: [
      {
        title: "Data used to run the app",
        items: [
          "Account information needed to sign in and find course access.",
          "Course workspace data such as uploaded source material, generated canvases, and approved media.",
          "Learner progress such as attendance mode, quiz attempts, readiness tasks, and generated study content.",
        ],
      },
      {
        title: "Data shared with model providers",
        items: [
          "Only the current tutor or course-builder request and the source excerpts needed to answer it.",
          "Generated image requests may include the prompt and the educational context needed for the image.",
          "Provider keys and routing are handled by the backend, not by the browser.",
        ],
      },
      {
        title: "Controls and boundaries",
        items: [
          "Learner-generated sections can be reset separately from professor-approved course material.",
          "Course managers can delete created course workspaces.",
          "Raw credentials, provider keys, and private course files should never be committed to the repository.",
        ],
      },
    ],
  },
};
