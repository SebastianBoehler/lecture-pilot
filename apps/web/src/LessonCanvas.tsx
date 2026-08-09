import { useEffect, useRef } from "react";

import { CanvasBlocks } from "./CanvasBlocks";
import { SectionSources } from "./SectionSources";
import { isLearnerGeneratedSection } from "./canvasSectionOrigin";
import type { CanvasLearningActions } from "./canvasLearningActions";
import type {
  CanvasDocument,
  CanvasSection,
  DocumentAnchorId,
  LoginSession,
  WorkspaceResource,
} from "./types";

export function LessonCanvas({
  canvasDocument,
  focusedSectionId,
  highlightedBlockId,
  highlightedText,
  activeAnchorId,
  navigationVersion,
  outlinePulseId,
  outlinePulseVersion,
  onOpenResource,
  onSubmitCheckpoint,
  onSubmitQuizAnswer,
  publicationVersion,
  quizStates,
  session,
}: {
  canvasDocument: CanvasDocument;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  activeAnchorId: DocumentAnchorId | null;
  navigationVersion: number;
  outlinePulseId: DocumentAnchorId | null;
  outlinePulseVersion: number;
  onOpenResource: (resource: WorkspaceResource) => void;
  session: LoginSession;
} & CanvasLearningActions) {
  const initialNavigationVersion = useRef(navigationVersion);

  useEffect(() => {
    if (navigationVersion === initialNavigationVersion.current) return;
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
      <h1>{canvasDocument.title}</h1>

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
          onSubmitCheckpoint,
          onSubmitQuizAnswer,
          publicationVersion,
          quizStates,
          session,
          navigationVersion,
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
  onSubmitCheckpoint,
  onSubmitQuizAnswer,
  publicationVersion,
  quizStates,
  session,
  navigationVersion,
}: {
  canvasDocument: CanvasDocument;
  section: CanvasSection;
  isFocused: boolean;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  outlinePulseId: DocumentAnchorId | null;
  outlinePulseVersion: number;
  onOpenResource: (resource: WorkspaceResource) => void;
  session: LoginSession;
  navigationVersion: number;
} & CanvasLearningActions) {
  const className = [
    "canvas-section",
    isFocused ? "is-focused" : "",
    isLearnerGeneratedSection(section) ? "is-learner-generated" : "",
    isFocused ? pulseClass(true, navigationVersion) : "",
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
      <h2 id={`${section.id}-heading`}>{section.title}</h2>
      <CanvasBlocks
        canvasDocument={canvasDocument}
        section={section}
        highlightedBlockId={highlightedBlockId}
        highlightedText={highlightedText}
        outlinePulseId={outlinePulseId}
        outlinePulseVersion={outlinePulseVersion}
        session={session}
        quizStates={quizStates}
        onOpenResource={onOpenResource}
        onSubmitCheckpoint={onSubmitCheckpoint}
        onSubmitQuizAnswer={onSubmitQuizAnswer}
        publicationVersion={publicationVersion}
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
