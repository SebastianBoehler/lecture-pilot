import { useEffect } from "react";

import { apiUrl } from "./api";
import { DisplayMath, MathText } from "./MathText";
import { SectionSources } from "./SectionSources";
import type {
  CanvasBlock,
  CanvasDocument,
  CanvasSection,
  DocumentAnchorId,
  Lecture,
  WorkspaceResource,
} from "./types";

export function LessonCanvas({
  canvasDocument,
  lecture,
  focusedSectionId,
  highlightedBlockId,
  highlightedText,
  activeAnchorId,
  navigationVersion,
  outlinePulseId,
  outlinePulseVersion,
  onOpenResource,
}: {
  canvasDocument: CanvasDocument;
  lecture: Lecture;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  activeAnchorId: DocumentAnchorId | null;
  navigationVersion: number;
  outlinePulseId: DocumentAnchorId | null;
  outlinePulseVersion: number;
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  useEffect(() => {
    const section = document.getElementById(focusedSectionId);
    if (typeof section?.scrollIntoView === "function") {
      section.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusedSectionId, navigationVersion]);

  useEffect(() => {
    const block = highlightedBlockId ? document.getElementById(highlightedBlockId) : null;
    if (typeof block?.scrollIntoView === "function") {
      block.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightedBlockId, navigationVersion]);

  function isActive(id: DocumentAnchorId) {
    return activeAnchorId ? activeAnchorId === id : focusedSectionId === id;
  }

  return (
    <article className="canvas">
      <p className="section-label">Lecture {lecture.number}</p>
      <h1>{canvasDocument.title}</h1>
      <p className="lead">
        A study document for probabilities, Bayes' rule, Naive Bayes classification, and
        risk-aware decisions.
      </p>

      {canvasDocument.sections.map((section) =>
        renderSection({
          canvasDocument,
          section,
          isFocused: isActive(section.id),
          highlightedBlockId,
          highlightedText,
          outlinePulseId,
          outlinePulseVersion,
          onOpenResource,
        }),
      )}
    </article>
  );
}

function renderSection({
  canvasDocument,
  section,
  isFocused,
  highlightedBlockId,
  highlightedText,
  outlinePulseId,
  outlinePulseVersion,
  onOpenResource,
}: {
  canvasDocument: CanvasDocument;
  section: CanvasSection;
  isFocused: boolean;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  outlinePulseId: DocumentAnchorId | null;
  outlinePulseVersion: number;
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  const className = [
    "canvas-section",
    isFocused ? "is-focused" : "",
    pulseClass(outlinePulseId === section.id, outlinePulseVersion),
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section
      aria-current={isFocused ? "true" : undefined}
      aria-labelledby={`${section.id}-heading`}
      className={className}
      id={section.id}
      key={section.id}
    >
      {isFocused ? <span className="focus-chip">In focus</span> : null}
      <h2 id={`${section.id}-heading`}>{section.title}</h2>
      {section.blocks.map((block) =>
        renderBlock(block, {
          isHighlighted: highlightedBlockId === block.id,
          isPulsed: outlinePulseId === block.id,
          highlightedText,
          outlinePulseVersion,
        }),
      )}
      <SectionSources
        canvasDocument={canvasDocument}
        section={section}
        onOpenResource={onOpenResource}
      />
    </section>
  );
}

function renderBlock(
  block: CanvasBlock,
  {
    isHighlighted,
    isPulsed,
    highlightedText,
    outlinePulseVersion,
  }: {
    isHighlighted: boolean;
    isPulsed: boolean;
    highlightedText: string | null;
    outlinePulseVersion: number;
  },
) {
  const className = [
    "canvas-block",
    isHighlighted ? "is-highlighted" : "",
    pulseClass(isPulsed, outlinePulseVersion),
  ]
    .filter(Boolean)
    .join(" ");
  const phrase = isHighlighted ? highlightedText : null;
  if (block.type === "list") {
    return (
      <ul className={`${className} canvas-list`} id={block.id} key={block.id}>
        {block.items.map((item) => (
          <li key={item}>
            <MathText highlightedText={phrase} text={item} />
          </li>
        ))}
      </ul>
    );
  }

  if (block.type === "asset" && block.asset_url) {
    return (
      <figure className={`${className} canvas-asset`} id={block.id} key={block.id}>
        <img alt={block.caption ?? "Course figure"} src={apiUrl(block.asset_url)} />
        {block.caption ? <figcaption>{block.caption}</figcaption> : null}
      </figure>
    );
  }

  if (block.type === "callout") {
    return (
      <aside className={`${className} canvas-callout`} id={block.id} key={block.id}>
        <MathText highlightedText={phrase} text={block.text ?? ""} />
      </aside>
    );
  }

  if (block.type === "math" && block.text) {
    return (
      <div
        className={`${className} canvas-math`}
        id={block.id}
        key={block.id}
      >
        <DisplayMath expression={block.text} />
      </div>
    );
  }

  return (
    <p className={className} id={block.id} key={block.id}>
      <MathText highlightedText={phrase} text={block.text ?? ""} />
    </p>
  );
}

function pulseClass(isPulsed: boolean, version: number) {
  if (!isPulsed) return "";
  return `is-outline-pulsed pulse-${version % 2 === 0 ? "even" : "odd"}`;
}
