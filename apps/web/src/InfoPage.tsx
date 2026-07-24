import { HowItWorksArticle } from "./HowItWorksArticle";
import { LearningScienceArticle } from "./LearningScienceArticle";
import type { InfoPageKind } from "./types";

export function InfoPage({ kind }: { kind: InfoPageKind }) {
  const content = kind === "privacy" ? PRIVACY_CONTENT : null;
  const isArticle = kind === "how-it-works" || kind === "learning-science";
  return (
    <main className={`info-page ${isArticle ? "is-how-it-works" : ""}`}>
      {content ? (
        <>
          <section className="info-hero">
            <h1>{content.title}</h1>
            <p>{content.intro}</p>
          </section>
          <article className="info-notice">
            {content.noticeSections.map((section) => (
              <section className="info-notice-section" key={section.title}>
                <h2>{section.title}</h2>
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </section>
            ))}
          </article>
        </>
      ) : kind === "learning-science" ? (
        <LearningScienceArticle />
      ) : (
        <HowItWorksArticle />
      )}
    </main>
  );
}

type NoticeContent = {
  title: string;
  intro: string;
  noticeSections: Array<{ title: string; paragraphs: string[] }>;
};

const PRIVACY_CONTENT: NoticeContent = {
  title: "Privacy notice",
  intro:
    "Your university account, course activity, and tutor requests help LecturePilot open the right workspace and support your learning. You can see below what is stored, what may be sent to an AI model provider, and what remains under course or learner control.",
  noticeSections: [
    {
      title: "Account and course access",
      paragraphs: [
        "When you sign in, LecturePilot uses your university account information to identify you and show the courses or demo workspaces available to you. Your sign-in request is handled by the LecturePilot service; your password is not stored in the web app or sent to an AI model provider.",
        "Your course access, role, and workspace membership determine whether you see a student workspace, professor course tools, or course analytics. This access information is used for authorization, not as input for general model training.",
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
        "When you ask the tutor a question, LecturePilot sends the AI model your request and the lecture context needed to answer it. Depending on the task, this can include selected source excerpts, the current canvas section, attendance mode, recent tutor messages, and the amount of guidance you should receive.",
        "If image generation is enabled, the request can include your prompt and the educational context needed to create the visual explanation. Provider API keys remain on the LecturePilot service and are never exposed to your browser.",
      ],
    },
    {
      title: "Analytics and professor view",
      paragraphs: [
        "Professor analytics show course-level learning signals such as published lectures, readiness attempts, quiz outcomes, weak topics, and progress. Course staff can use these signals to improve teaching and identify where students need support.",
        "Course staff do not see your ordinary private chat transcripts or personal canvas in course analytics. If a course adds review, moderation, or research logging beyond these aggregates, you must be told separately before it begins.",
      ],
    },
    {
      title: "Storage and deletion",
      paragraphs: [
        "Course managers can delete course workspaces. You can reset learner-generated sections without changing professor-approved material. Final retention periods, backup expiry, and the process for requesting access, correction, or deletion still need institutional approval.",
        "LecturePilot is currently a university pilot. The responsible institution, contact details, legal basis, retention schedule, AI providers, data rights, and final hosting location will be added here before broader use.",
      ],
    },
  ],
};
