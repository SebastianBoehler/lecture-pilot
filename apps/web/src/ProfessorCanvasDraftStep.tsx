import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import type { CanvasDocument } from "./types";

export function ProfessorCanvasDraftStep({
  canvas,
  canGenerate,
  generatedCount,
  isFullCourse,
  isGenerating,
  onGenerate,
  previewHref,
  totalCount,
}: {
  canvas: CanvasDocument | null;
  canGenerate: boolean;
  generatedCount: number;
  isFullCourse: boolean;
  isGenerating: boolean;
  onGenerate: () => void;
  previewHref: string | null;
  totalCount: number;
}) {
  const actionLabel = isFullCourse ? "Generate all lecture canvases" : "Generate draft canvas";
  const busyLabel = isFullCourse ? "Generating lecture canvases..." : "Generating draft canvas...";
  const statusLabel = isFullCourse
    ? `Generating source-grounded canvases for ${totalCount} lectures...`
    : "Generating a source-grounded canvas draft...";
  return (
    <section className="flow-card">
      <StepHeader number="04" title="Generate canvas draft" done={Boolean(canvas)} />
      <button className="primary-action" disabled={!canGenerate || isGenerating} type="button" onClick={onGenerate}>
        {isGenerating ? busyLabel : actionLabel}
      </button>
      {isGenerating ? <PendingStatus label={statusLabel} /> : null}
      {canvas && isFullCourse ? <p>{generatedCount} lecture canvases ready for publication.</p> : null}
      {canvas && !isFullCourse ? <p>{canvas.sections.length} sections ready for review.</p> : null}
      {previewHref ? (
        <a className="button-link" href={previewHref} rel="noreferrer" target="_blank">
          Preview course workspace
        </a>
      ) : (
        <button disabled type="button">
          Preview course workspace
        </button>
      )}
    </section>
  );
}
