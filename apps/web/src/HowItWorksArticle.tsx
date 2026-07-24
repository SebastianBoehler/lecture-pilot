import { Bot, FileText, FolderOpen, LockKeyhole } from "lucide-react";

export function HowItWorksArticle() {
  return (
    <article className="how-article">
      <header className="how-hero">
        <h1>How LecturePilot actually works</h1>
        <p>
          LecturePilot looks like a tutor chat, but the chat is only the visible part. Underneath is
          a controlled learning workspace where course material, student progress, and an AI agent
          can work together without becoming one big, unstructured conversation.
        </p>
      </header>

      <section aria-labelledby="model-heading">
        <h2 id="model-heading">The model is only one part of the tutor</h2>
        <p>
          A language model can write a plausible explanation, but it does not automatically know
          which lecture you are in, what your professor has approved, or what you already tried.
          LecturePilot supplies that missing structure.
        </p>
        <p>
          The <strong>agent harness</strong> is the software around the model. It decides which
          workspace the tutor may enter, which tools it may use, which teaching rules apply, and
          which changes should be saved for the next session.
        </p>
      </section>

      <section aria-labelledby="course-heading">
        <h2 id="course-heading">Every course has its own workspace</h2>
        <p>
          Slides, PDFs, LaTeX files, images, and the published lecture canvas live together in a
          structured course workspace. Together, they form the <em>course image</em>: the organized
          view of the course that the tutor is allowed to work inside.
        </p>
        <p>
          Machine Learning and Macroeconomics therefore do not blur into the same memory. Each
          course has its own sources, lectures, terminology, and teaching path.
        </p>
        <WorkspaceFigure />
      </section>

      <section aria-labelledby="private-layer-heading">
        <h2 id="private-layer-heading">Each student gets a private layer on top</h2>
        <p>
          Everyone in a course can learn from the same approved material, but the tutor does not
          write back into the professor&apos;s files. Your notes, generated explanations, quiz
          attempts, progress, and learning preferences belong to your own layer.
        </p>
        <p>
          That separation is what makes adaptation useful. The tutor can remember that you needed a
          geometric explanation yesterday without changing the course for everyone else—or showing
          your private notebook to another student or professor.
        </p>
      </section>

      <section aria-labelledby="harness-heading">
        <h2 id="harness-heading">The agent works through a small set of real tools</h2>
        <p>
          Instead of asking the model to pretend it has read a lecture, the backend gives it a small
          toolbox for the current workspace. It can inspect relevant material, teach with that
          context, and save useful additions to the learner&apos;s canvas. It cannot simply roam
          around the server or open another student&apos;s files.
        </p>
        <ToolFigure />
      </section>

      <section aria-labelledby="turn-heading">
        <h2 id="turn-heading">What happens when you ask a question</h2>
        <p>
          A tutor response is a short workflow rather than a single prompt sent blindly to a model.
          The important context is selected first, and any lasting change is written back through
          the harness.
        </p>
        <TutorTurn />
      </section>

      <section aria-labelledby="professor-heading">
        <h2 id="professor-heading">What professors see</h2>
        <p>
          Course analytics can reveal that a quiz is frequently missed or that a topic needs another
          explanation. They are not a window into ordinary student chats or personal canvases. The
          useful unit is the learning signal across the course, not surveillance of an individual.
        </p>
        <p className="how-conclusion">
          LecturePilot does not ask a chatbot to know everything. It gives the tutor the right
          course context, useful tools, and clear boundaries.
        </p>
      </section>
    </article>
  );
}

function WorkspaceFigure() {
  return (
    <figure className="workspace-figure" aria-labelledby="workspace-figure-title">
      <div className="workspace-figure-bar">
        <span />
        <span />
        <span />
        <strong id="workspace-figure-title">Bayesian Decision Theory</strong>
      </div>
      <div className="workspace-tree">
        <div className="workspace-layer is-course">
          <span className="workspace-tree-path">course-image/</span>
          <span>One approved world for this course</span>
        </div>
        <div className="workspace-tree-branch">
          <span>├─ source/</span>
          <small>slides, PDFs, figures</small>
        </div>
        <div className="workspace-tree-branch">
          <span>└─ canvas/</span>
          <small>published lectures and sources</small>
        </div>
        <div className="workspace-layer is-learner">
          <span className="workspace-tree-path">your-layer/</span>
          <span>Private and shaped by your learning</span>
        </div>
        <div className="workspace-tree-branch">
          <span>├─ progress</span>
          <small>checks and attempts</small>
        </div>
        <div className="workspace-tree-branch">
          <span>├─ notes</span>
          <small>your explanations</small>
        </div>
        <div className="workspace-tree-branch">
          <span>└─ generated/</span>
          <small>examples and visuals</small>
        </div>
      </div>
      <figcaption>A simplified view: shared course truth, separate learner work.</figcaption>
    </figure>
  );
}

function ToolFigure() {
  const tools = [
    [FolderOpen, "Look", "Open the relevant lecture and find source-backed context."],
    [Bot, "Teach", "Explain a difficult step or choose a more demanding follow-up."],
    [FileText, "Create", "Add a learner-owned note, example, quiz, or visual."],
    [LockKeyhole, "Stay bounded", "Remain inside the permitted user, course, and lecture."],
  ] as const;
  return (
    <ul className="how-tools" aria-label="Tools available to the LecturePilot agent">
      {tools.map(([Icon, title, description]) => (
        <li key={title}>
          <Icon size={18} aria-hidden="true" />
          <p>
            <strong>{title}</strong>
            <span>{description}</span>
          </p>
        </li>
      ))}
    </ul>
  );
}

function TutorTurn() {
  const steps = [
    ["You ask", "Why does the Bayes decision rule choose the smallest expected loss?"],
    [
      "The harness scopes",
      "Your account, this course, this lecture, and the relevant canvas section.",
    ],
    ["The agent reads", "The approved source passage plus the progress needed for this question."],
    [
      "The tutor teaches",
      "It explains, checks understanding, and can add an example to your canvas.",
    ],
  ];
  return (
    <ol className="how-turn">
      {steps.map(([title, description], index) => (
        <li key={title}>
          <span className="how-step-number">{String(index + 1).padStart(2, "0")}</span>
          <p>
            <strong>{title}</strong>
            <span>{description}</span>
          </p>
        </li>
      ))}
    </ol>
  );
}
