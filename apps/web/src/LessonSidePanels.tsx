import { documentOutlineItems } from "./lessonOutline";
import type { DocumentAnchorId, Lecture } from "./types";

export function OutlinePanel({
  activeAnchorId,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  return (
    <aside className="drawer" aria-label="Document outline panel">
      <div className="drawer-section">
        <h2>Document outline</h2>
        <p className="drawer-note">
          Navigate the lesson document by sections, source packets, checks, and embedded media.
        </p>
        <nav className="outline-list" aria-label="Lesson document outline">
          {documentOutlineItems.map((item) => (
            <button
              className={activeAnchorId === item.id ? "is-active" : undefined}
              type="button"
              aria-pressed={activeAnchorId === item.id}
              key={item.id}
              onClick={() => onJumpAnchor(item.id)}
            >
              <span>{item.kind}</span>
              {item.title}
            </button>
          ))}
        </nav>
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
