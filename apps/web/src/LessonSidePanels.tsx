import { useI18n } from "./i18n";
import { LessonDrawerClose } from "./LessonDrawerClose";
import type { CanvasBlock, CanvasDocument, DocumentAnchorId, Lecture } from "./types";

export function OutlinePanel({
  activeAnchorId,
  canvasDocument,
  onClose,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  canvasDocument: CanvasDocument | null;
  onClose: () => void;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  const { t } = useI18n();
  return (
    <aside className="drawer" id="lesson-panel" aria-label={t("outline.panel")}>
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-outline" onClose={onClose} />
      <div className="drawer-section">
        <h2>{t("outline.title")}</h2>
        <nav className="outline-tree" aria-label={t("outline.nav")}>
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
                    mainPointLabel: t("outline.mainPoint"),
                    variant: "section",
                  })}
                  {interestBlocks.length ? (
                    <div
                      aria-label={t("outline.relatedItems", { section: section.title })}
                      className="outline-children"
                      role="group"
                    >
                      {interestBlocks.map((block) =>
                        renderOutlineNode({
                          id: block.id,
                          title: blockTitle(block, t),
                          kind: outlineKind(block),
                          kindLabel: outlineKindLabel(block, t),
                          activeAnchorId,
                          mainPointLabel: t("outline.mainPoint"),
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
            <p className="drawer-note">{t("outline.loading")}</p>
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
  kindLabel,
  activeAnchorId,
  mainPointLabel,
  onJumpAnchor,
  index,
  variant,
}: {
  id: string;
  title: string;
  kind: string;
  kindLabel?: string;
  activeAnchorId: DocumentAnchorId | null;
  mainPointLabel: string;
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
        {variant === "section" ? <span className="outline-kind">{mainPointLabel}</span> : null}
        <span className="outline-title">{title}</span>
        {variant === "child" ? <span className="outline-kind">{kindLabel ?? kind}</span> : null}
      </span>
    </button>
  );
}

function blockTitle(
  block: CanvasBlock,
  t: (key: "outline.kind.keyPoint" | "outline.listTitle") => string,
) {
  if (block.caption) {
    return block.caption;
  }
  if (block.text) {
    return outlineTextExcerpt(block.text);
  }
  if (block.type === "list") {
    return t("outline.listTitle");
  }
  return block.type;
}

function outlineInterestBlocks(blocks: CanvasBlock[]) {
  const preferredTypes: CanvasBlock["type"][] = [
    "checkpoint",
    "component",
    "quiz",
    "table",
    "list",
    "video",
    "asset",
    "callout",
  ];
  const result: CanvasBlock[] = [];
  for (const type of preferredTypes) {
    const block = blocks.find((candidate) => candidate.type === type);
    if (block) result.push(block);
  }
  return result.slice(0, 3);
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
  if (block.type === "checkpoint") {
    return "gate";
  }
  if (block.type === "quiz") {
    return "quiz";
  }
  if (block.type === "component") {
    return "interactive";
  }
  return block.type;
}

function outlineKindLabel(
  block: CanvasBlock,
  t: (
    key:
      | "outline.kind.figure"
      | "outline.kind.video"
      | "outline.kind.keyPoint"
      | "outline.kind.gate"
      | "outline.kind.quiz"
      | "outline.kind.interactive",
  ) => string,
) {
  if (block.type === "asset") return t("outline.kind.figure");
  if (block.type === "video") return t("outline.kind.video");
  if (block.type === "list") return t("outline.kind.keyPoint");
  if (block.type === "checkpoint") return t("outline.kind.gate");
  if (block.type === "quiz") return t("outline.kind.quiz");
  if (block.type === "component") return t("outline.kind.interactive");
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

export function NotesPanel({ lecture, onClose }: { lecture: Lecture; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <aside className="drawer" id="lesson-panel" aria-label={t("notes.panel")}>
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-notes" onClose={onClose} />
      <div className="drawer-section">
        <h2>{t("notes.title")}</h2>
        <div className="source-list">
          <article>
            <span>{t("notes.officialSource")}</span>
            <strong>{lecture.materialPath ?? "courses/martius-ml/lectures/03/source.tex"}</strong>
          </article>
          <article>
            <span>{t("notes.timelineGate")}</span>
            <strong>{t("notes.unlocked", { date: lecture.date })}</strong>
          </article>
          <article>
            <span>{t("notes.attendanceContext")}</span>
            <strong>{lecture.attendance}</strong>
          </article>
        </div>
      </div>
    </aside>
  );
}
