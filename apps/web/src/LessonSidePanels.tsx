import type { CanvasBlock, CanvasDocument, DocumentAnchorId, Lecture } from "./types";

export function OutlinePanel({
  activeAnchorId,
  canvasDocument,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  canvasDocument: CanvasDocument | null;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  return (
    <aside className="drawer" aria-label="Document outline panel">
      <div className="drawer-section">
        <h2>Document outline</h2>
        <nav className="outline-tree" aria-label="Lesson document outline">
          {canvasDocument ? (
            canvasDocument.sections.map((section, index) => (
              <section className="outline-group" key={section.id}>
              {renderOutlineNode({
                id: section.id,
                title: section.title,
                kind: "section",
                activeAnchorId,
                onJumpAnchor,
                index,
                variant: "section",
              })}
              <div
                aria-label={`${section.title} related items`}
                className="outline-children"
                role="group"
              >
                {section.blocks.map((block) =>
                  renderOutlineNode({
                    id: block.id,
                    title: blockTitle(block),
                    kind: block.type,
                    activeAnchorId,
                    onJumpAnchor,
                    variant: "child",
                  }),
                )}
              </div>
              </section>
            ))
          ) : (
            <p className="drawer-note">Canvas loading...</p>
          )}
        </nav>
      </div>
    </aside>
  );
}

function renderOutlineNode({
  id,
  title,
  kind,
  activeAnchorId,
  onJumpAnchor,
  index,
  variant,
}: {
  id: string;
  title: string;
  kind: string;
  activeAnchorId: DocumentAnchorId | null;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
  index?: number;
  variant: "section" | "child";
}) {
  const isActive = activeAnchorId === id;

  return (
    <button
      aria-label={title}
      aria-pressed={isActive}
      className={`outline-node ${variant} ${isActive ? "is-active" : ""}`}
      key={id}
      onClick={() => onJumpAnchor(id)}
      type="button"
    >
      {variant === "section" ? (
        <span className="outline-index">{String((index ?? 0) + 1).padStart(2, "0")}</span>
      ) : (
        <span className={`outline-marker ${kind}`} aria-hidden="true" />
      )}
      <span className="outline-copy">
        {variant === "section" ? <span className="outline-kind">Main point</span> : null}
        <span className="outline-title">{title}</span>
        {variant === "child" ? <span className="outline-kind">{kind}</span> : null}
      </span>
    </button>
  );
}

function blockTitle(block: CanvasBlock) {
  if (block.caption) {
    return block.caption;
  }
  if (block.type === "list") {
    return "Key points";
  }
  if (block.type === "math") {
    return "Formula";
  }
  if (block.text) {
    return outlineTextExcerpt(block.text);
  }
  return block.type;
}

function outlineTextExcerpt(text: string) {
  const cleaned = text
    .replace(/\$[^$]+\$/g, "Formula")
    .replace(/\\\((.*?)\\\)/g, "Formula")
    .replace(/\\[a-zA-Z]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.split(" ").slice(0, 6).join(" ");
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
