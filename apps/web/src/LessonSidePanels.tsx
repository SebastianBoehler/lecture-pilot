import { OutlineProgress } from "./OutlineProgress";
import { practiceStatus } from "./practiceStatus";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import { useI18n } from "./i18n";
import { LessonDrawerClose } from "./LessonDrawerClose";
import type { CanvasBlock, CanvasDocument, DocumentAnchorId } from "./types";

export function OutlinePanel({
  activeAnchorId,
  canvasDocument,
  learnerState = null,
  onClose,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  canvasDocument: CanvasDocument | null;
  learnerState?: LearnerLessonState | null;
  onClose: () => void;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  const { t } = useI18n();
  return (
    <aside className="drawer outline-drawer" id="lesson-panel" aria-label={t("outline.panel")}>
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-outline" onClose={onClose} />
      <div className="drawer-section">
        <h2>{t("outline.title")}</h2>
        <OutlineProgress state={learnerState} onJumpAnchor={onJumpAnchor} />
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
                          fullTitle: block.caption ?? block.text ?? undefined,
                          kind: outlineKind(block),
                          kindLabel:
                            block.type === "checkpoint" || block.type === "quiz"
                              ? t(practiceStatus(block.type, block.id, learnerState))
                              : outlineKindLabel(block, t),
                          currentCheck:
                            learnerState?.pending_check?.gate_id === block.id
                              ? t("outline.currentCheck")
                              : undefined,
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
  fullTitle,
  kind,
  kindLabel,
  activeAnchorId,
  currentCheck,
  onJumpAnchor,
  index,
  variant,
}: {
  id: string;
  title: string;
  fullTitle?: string;
  kind: string;
  kindLabel?: string;
  activeAnchorId: DocumentAnchorId | null;
  currentCheck?: string;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
  index?: number;
  variant: "section" | "child";
}) {
  const isActive = activeAnchorId === id;

  return (
    <button
      aria-label={title}
      title={fullTitle}
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
        {currentCheck ? <span className="outline-current-check">{currentCheck}</span> : null}
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
  if ((block.type === "checkpoint" || block.type === "quiz") && block.text) {
    if (
      block.caption &&
      !/^(checkpoint|quiz|quick check|lernzielkontrolle)$/i.test(block.caption.trim())
    ) {
      return block.caption;
    }
    return outlineTextExcerpt(block.text);
  }
  if (block.caption) {
    return block.caption.replace(/^((?:Original|Compiled) slide \d+) from .+$/, "$1");
  }
  if (block.type === "table" && block.text) {
    return outlineTextExcerpt(block.text.split("\n")[0].replace(/\|/g, " "));
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
  const assessments = blocks.filter(
    (block) => block.type === "checkpoint" || block.type === "quiz",
  );
  const preferredTypes: CanvasBlock["type"][] = [
    "component",
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
  return [...assessments, ...result.slice(0, Math.max(1, 3 - assessments.length))];
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
    return "check";
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
      | "outline.kind.interactive"
      | "outline.kind.note"
      | "outline.kind.table",
  ) => string,
) {
  if (block.type === "callout") return t("outline.kind.note");
  if (block.type === "table") return t("outline.kind.table");
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
    .replace(/\*\*|__|`/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const words = cleaned.split(" ");
  return words.length > 10 ? `${words.slice(0, 10).join(" ")}…` : cleaned;
}
