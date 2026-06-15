import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import type { CanvasDocument } from "./types";

export function ProfessorCanvasDraftStep({
  canvas,
  canGenerate,
  isGenerating,
  onGenerate,
  previewHref,
}: {
  canvas: CanvasDocument | null;
  canGenerate: boolean;
  isGenerating: boolean;
  onGenerate: () => void;
  previewHref: string | null;
}) {
  return (
    <section className="flow-card">
      <StepHeader number="03" title="Generate canvas draft" done={Boolean(canvas)} />
      <button disabled={!canGenerate || isGenerating} type="button" onClick={onGenerate}>
        {isGenerating ? "Generating draft canvas..." : "Generate draft canvas"}
      </button>
      {isGenerating ? <PendingStatus label="Generating a source-grounded canvas draft..." /> : null}
      {canvas ? <p>{canvas.sections.length} sections ready for review.</p> : null}
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
