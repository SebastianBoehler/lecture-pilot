import type { InfoPageKind } from "./types";

export function InfoPage({ kind, onBack }: { kind: InfoPageKind; onBack: () => void }) {
  const content = INFO_CONTENT[kind];
  return (
    <main className="info-page">
      <button className="ghost-button info-back" type="button" onClick={onBack}>Back</button>
      <section className="info-hero">
        <h1>{content.title}</h1>
        <p>{content.intro}</p>
      </section>
      {"noticeSections" in content ? (
        <article className="info-notice">
          {content.noticeSections.map((section) => (
            <section className="info-notice-section" key={section.title}>
              <h2>{section.title}</h2>
              {section.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </section>
          ))}
        </article>
      ) : (
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
      )}
    </main>
  );
}

type OverviewContent = {
  title: string;
  intro: string;
  sections: Array<{ title: string; items: string[] }>;
};

type NoticeContent = {
  title: string;
  intro: string;
  noticeSections: Array<{ title: string; paragraphs: string[] }>;
};

const INFO_CONTENT: Record<InfoPageKind, OverviewContent | NoticeContent> = {
  "how-it-works": {
    title: "How LecturePilot works",
    intro: "LecturePilot is an agent harness for learning. The tutor works inside a controlled course workspace, uses tools to read and create files, and turns lecture material into a canvas that can adapt to what the student already understands.",
    sections: [
      {
        title: "A course workspace",
        items: [
          "Think of each course as a small file system with lecture sources, approved canvas sections, learner notes, generated images, quiz attempts, and progress.",
          "Official professor material stays in the course area. Student-specific explanations and notes are written into the learner's own workspace.",
          "The tutor can only use the files and tools the backend exposes for the current course and lecture.",
        ],
      },
      {
        title: "An agent with tools",
        items: [
          "The agent can pull up the relevant lecture files, inspect the current canvas, and find source-backed context before answering.",
          "It can create or update learner-owned files on the fly, for example an extra explanation, a visual example, a checkpoint, or a practice section.",
          "Those file changes become visible in the learning canvas instead of staying hidden inside a chat transcript.",
        ],
      },
      {
        title: "An adaptive teaching loop",
        items: [
          "The tutor uses attendance, quiz attempts, quality gates, and recent answers to estimate the student's current level for this lecture.",
          "If the student is missing foundations, the agent gives more scaffolding and concrete examples. If the student is stronger, it asks for transfer, evidence, and exam-style reasoning.",
          "Professor analytics use learning signals and progress patterns, while private learner content remains separate from official course material.",
        ],
      },
    ],
  },
  privacy: {
    title: "Privacy notice",
    intro: "This page explains in plain language what LecturePilot uses data for, when data may be sent to model providers, and what stays under course or learner control.",
    noticeSections: [
      {
        title: "Account and course access",
        paragraphs: [
          "When you sign in, LecturePilot uses your university account information only to identify you and to determine which courses or demo workspaces should be available. The browser sends the sign-in request to the LecturePilot backend; the frontend does not store your password or send it directly to an AI model provider.",
          "Course access, role information, and workspace membership are used to decide whether you see the student workspace, professor course tools, or course analytics. These checks are part of the product workflow, not input for general model training.",
        ],
      },
      {
        title: "Course material and learning workspace",
        paragraphs: [
          "Professors can upload course material such as slides, LaTeX sources, PDFs, images, and approved media links. LecturePilot processes this material to create lecture canvases, source references, quizzes, and study sections. Official course material is kept separate from learner-owned notes and generated study content.",
          "As a learner, your workspace can contain attendance mode, lecture progress, quiz attempts, readiness attempts, generated notes, generated images, and course-specific tutor memory. This data is used to continue your learning session, adapt guidance to what you have already done, and show aggregate learning signals to course staff.",
        ],
      },
      {
        title: "AI tutor and model requests",
        paragraphs: [
          "When you ask the tutor a question, the backend sends the model only the current request plus the relevant lecture context needed to answer it. That can include selected source excerpts, the current canvas section, attendance mode, recent tutor messages, and the scaffold policy for the learning task.",
          "If image generation is enabled, an image request can include the prompt and the educational context needed to create the visual explanation. Provider keys and model routing stay on the backend. They are not exposed to the browser.",
        ],
      },
      {
        title: "Analytics and professor view",
        paragraphs: [
          "Professor analytics are intended to show learning signals such as published lectures, readiness attempts, quiz outcomes, weak topics, and course-level progress. The goal is to help improve teaching and identify where students need support.",
          "The product should not expose raw private chat transcripts as ordinary professor analytics. If a deployment needs review, moderation, or research logging, that must be stated separately before the course starts.",
        ],
      },
      {
        title: "Storage, deletion, and production requirements",
        paragraphs: [
          "Course managers can delete created course workspaces, and learner-generated sections can be reset separately from professor-approved material. A production deployment should also define retention periods, audit logging, backup behavior, and who can request deletion or correction.",
          "Before LecturePilot is used beyond a pilot or demo, this notice must be completed with the responsible institution, contact details, legal basis, retention schedule, subprocessors, data subject rights, and the final hosting location.",
        ],
      },
    ],
  },
};
