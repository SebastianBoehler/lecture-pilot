import type { Lecture } from "./types";

export function ArtifactsPanel() {
  const presets = ["Summary", "Quiz", "Code", "Diagram"];

  return (
    <aside className="drawer" aria-label="Artifacts panel">
      <div className="drawer-section">
        <h2>Artifacts</h2>
        <div className="artifact-actions" aria-label="Artifact presets">
          {presets.map((preset) => (
            <button type="button" key={preset}>
              {preset}
            </button>
          ))}
        </div>
        <div className="artifact-card">
          <h3>Gate: Kernel Skill Check</h3>
          <p>Ready means you can name the replaced computation and explain why it saves work.</p>
        </div>
        <div className="artifact-card">
          <h3>Canvas Action</h3>
          <p>The tutor can open generated summaries, quizzes, code cells, or diagrams here.</p>
        </div>
      </div>
    </aside>
  );
}

export function NotesPanel({ lecture }: { lecture: Lecture }) {
  return (
    <aside className="drawer" aria-label="Lecture notes panel">
      <div className="drawer-section">
        <h2>Source notes</h2>
        <div className="source-list">
          <article>
            <span>Official LaTeX source</span>
            <strong>{lecture.materialPath ?? "courses/martius-ml/lectures/03/source.tex"}</strong>
          </article>
          <article>
            <span>Timeline gate</span>
            <strong>{lecture.date} · already unlocked</strong>
          </article>
          <article>
            <span>Attendance context</span>
            <strong>{lecture.attendance}</strong>
          </article>
        </div>
      </div>
    </aside>
  );
}
