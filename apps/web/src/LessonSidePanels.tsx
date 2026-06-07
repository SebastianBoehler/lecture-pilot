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
            canvasDocument.sections.map((section, index) => {
              const interestBlocks = outlineInterestBlocks(section.blocks);
              return (
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
                  {interestBlocks.length ? (
                    <div
                      aria-label={`${section.title} related items`}
                      className="outline-children"
                      role="group"
                    >
                      {interestBlocks.map((block) =>
                        renderOutlineNode({
                          id: block.id,
                          title: blockTitle(block),
                          kind: outlineKind(block),
                          activeAnchorId,
                          onJumpAnchor,
                          variant: "child",
                        }),
                      )}
                    </div>
                  ) : null}
                </section>
              );
            })
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
    return "Key ideas";
  }
  if (block.text) {
    return outlineTextExcerpt(block.text);
  }
  return block.type;
}

function outlineInterestBlocks(blocks: CanvasBlock[]) {
  const preferredTypes: CanvasBlock["type"][] = ["list", "video", "asset", "callout"];
  const result: CanvasBlock[] = [];
  for (const type of preferredTypes) {
    const block = blocks.find((candidate) => candidate.type === type);
    if (block) result.push(block);
  }
  return result.slice(0, 3);
}

function isOutlineInterest(block: CanvasBlock) {
  return block.type === "asset" || block.type === "video" || block.type === "callout" || block.type === "list";
}

function outlineKind(block: CanvasBlock) {
  if (block.type === "asset") {
    return "figure";
  }
  if (block.type === "video") {
    return "video";
  }
  if (block.type === "list") {
    return "key point";
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
