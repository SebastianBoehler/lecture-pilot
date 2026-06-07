import { useEffect } from "react";

import { CanvasBlocks } from "./CanvasBlocks";
import { SectionSources } from "./SectionSources";
import type {
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
      <CanvasBlocks
        canvasDocument={canvasDocument}
        section={section}
        highlightedBlockId={highlightedBlockId}
        highlightedText={highlightedText}
        outlinePulseId={outlinePulseId}
        outlinePulseVersion={outlinePulseVersion}
        onOpenResource={onOpenResource}
      />
      <SectionSources
        canvasDocument={canvasDocument}
        section={section}
        onOpenResource={onOpenResource}
      />
    </section>
  );
}

function pulseClass(isPulsed: boolean, version: number) {
  if (!isPulsed) return "";
  return `is-outline-pulsed pulse-${version % 2 === 0 ? "even" : "odd"}`;
}
