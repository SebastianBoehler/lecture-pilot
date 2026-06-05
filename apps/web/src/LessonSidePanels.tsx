import { artifactBlocks } from "./ArtifactBlocks";
import type { ArtifactBlockId, Lecture } from "./types";

export function ArtifactsPanel({
  focusedArtifactId,
  onJumpArtifact,
}: {
  focusedArtifactId: ArtifactBlockId | null;
  onJumpArtifact: (artifactId: ArtifactBlockId) => void;
}) {
  return (
    <aside className="drawer" aria-label="Artifacts panel">
      <div className="drawer-section">
        <h2>Artifact index</h2>
        <p className="drawer-note">
          Generated blocks live in the lesson canvas. Use this overview to jump through the document.
        </p>
        <nav className="artifact-jump-list" aria-label="Generated artifact blocks">
          {artifactBlocks.map((artifact) => (
            <button
              className={focusedArtifactId === artifact.id ? "is-active" : undefined}
              type="button"
              aria-pressed={focusedArtifactId === artifact.id}
              key={artifact.id}
              onClick={() => onJumpArtifact(artifact.id)}
            >
              Jump to {artifact.title}
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
