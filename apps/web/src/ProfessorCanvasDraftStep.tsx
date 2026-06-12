import { StepHeader } from "./ProfessorCourseBuilderParts";
import type { CanvasDocument } from "./types";

export function ProfessorCanvasDraftStep({
  canvas,
  canGenerate,
  onGenerate,
  previewHref,
}: {
  canvas: CanvasDocument | null;
  canGenerate: boolean;
  onGenerate: () => void;
  previewHref: string | null;
}) {
  return (
    <section className="flow-card">
      <StepHeader number="03" title="Generate canvas draft" done={Boolean(canvas)} />
      <button disabled={!canGenerate} type="button" onClick={onGenerate}>
        Generate draft canvas
      </button>
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
