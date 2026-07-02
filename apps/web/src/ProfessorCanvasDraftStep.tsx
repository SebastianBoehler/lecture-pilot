import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import { ProfessorGenerationWarnings } from "./ProfessorGenerationWarnings";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import type { CanvasDocument } from "./types";

export function ProfessorCanvasDraftStep({
  canvas,
  canGenerate,
  generationProgress,
  generatedCount,
  isFullCourse,
  isGenerating,
  warnings,
  onGenerate,
  previewHref,
  totalCount,
}: {
  canvas: CanvasDocument | null;
  canGenerate: boolean;
  generationProgress: CanvasGenerationProgress[];
  generatedCount: number;
  isFullCourse: boolean;
  isGenerating: boolean;
  onGenerate: () => void;
  previewHref: string | null;
  totalCount: number;
  warnings: string[];
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
      {generationProgress.length ? <GenerationProgressList progress={generationProgress} /> : null}
      <ProfessorGenerationWarnings warnings={warnings} />
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

function GenerationProgressList({ progress }: { progress: CanvasGenerationProgress[] }) {
  return (
    <div className="generation-progress" aria-label="Lecture generation progress">
      {progress.map((item) => (
        <div className={`generation-progress-row is-${item.status}`} key={item.lectureId}>
          <span>{item.lectureId.replace("lecture-", "Lecture ")}</span>
          <strong>{item.status}</strong>
          {item.message ? <small>{item.message}</small> : null}
        </div>
      ))}
    </div>
  );
}
