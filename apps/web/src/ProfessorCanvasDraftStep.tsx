import { useI18n } from "./i18n";
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
  const { t } = useI18n();
  const actionLabel = isFullCourse ? t("builder.generate.all") : t("builder.generate.single");
  const busyLabel = isFullCourse ? t("builder.generate.busyAll") : t("builder.generate.busySingle");
  const statusLabel = isFullCourse
    ? t("builder.generate.statusAll", { count: totalCount })
    : t("builder.generate.statusSingle");
  return (
    <section className="flow-card">
      <StepHeader number="04" title={t("builder.generate.title")} done={Boolean(canvas)} />
      <button
        className="primary-action"
        disabled={!canGenerate || isGenerating}
        type="button"
        onClick={onGenerate}
      >
        {isGenerating ? busyLabel : actionLabel}
      </button>
      {isGenerating ? <PendingStatus label={statusLabel} /> : null}
      {generationProgress.length ? <GenerationProgressList progress={generationProgress} /> : null}
      <ProfessorGenerationWarnings warnings={warnings} />
      {canvas && isFullCourse ? (
        <p>{t("builder.generate.fullReady", { count: generatedCount })}</p>
      ) : null}
      {canvas && !isFullCourse ? (
        <p>{t("builder.generate.singleReady", { count: canvas.sections.length })}</p>
      ) : null}
      {previewHref ? (
        <a className="button-link" href={previewHref} rel="noreferrer" target="_blank">
          {t("builder.generate.preview")}
        </a>
      ) : (
        <button disabled type="button">
          {t("builder.generate.preview")}
        </button>
      )}
    </section>
  );
}

function GenerationProgressList({ progress }: { progress: CanvasGenerationProgress[] }) {
  const { t } = useI18n();
  return (
    <div className="generation-progress" aria-label={t("builder.generate.progress")}>
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
