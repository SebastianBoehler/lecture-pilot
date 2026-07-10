import { useI18n } from "./i18n";
import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import type { CanvasDocument } from "./types";

export function ProfessorCanvasDraftStep({
  canvas,
  canGenerate,
  generationProgress,
  generatedCount,
  isFullCourse,
  isGenerating,
  onContinueToPublish,
  onGenerate,
  previewLectures,
  totalCount,
}: {
  canvas: CanvasDocument | null;
  canGenerate: boolean;
  generationProgress: CanvasGenerationProgress[];
  generatedCount: number;
  isFullCourse: boolean;
  isGenerating: boolean;
  onContinueToPublish: () => void;
  onGenerate: () => void;
  previewLectures: {
    id: string;
    label: string;
    previewHref: string;
  }[];
  totalCount: number;
}) {
  const { t } = useI18n();
  const actionLabel = isFullCourse ? t("builder.generate.all") : t("builder.generate.single");
  const busyLabel = isFullCourse ? t("builder.generate.busyAll") : t("builder.generate.busySingle");
  const statusLabel = isFullCourse
    ? t("builder.generate.statusAll", { count: totalCount })
    : t("builder.generate.statusSingle");
  const hasDraft = Boolean(canvas);
  return (
    <section className="flow-card">
      <StepHeader number="04" title={t("builder.generate.title")} done={hasDraft} />
      <button
        className={hasDraft ? undefined : "primary-action"}
        disabled={!canGenerate || isGenerating}
        type="button"
        onClick={onGenerate}
      >
        {isGenerating ? busyLabel : hasDraft ? t("builder.generate.regenerate") : actionLabel}
      </button>
      {isGenerating ? <PendingStatus label={statusLabel} /> : null}
      {generationProgress.length ? <GenerationProgressList progress={generationProgress} /> : null}
      {hasDraft && isFullCourse ? (
        <p>{t("builder.generate.fullReady", { count: generatedCount })}</p>
      ) : null}
      {canvas && !isFullCourse ? (
        <p>{t("builder.generate.singleReady", { count: canvas.sections.length })}</p>
      ) : null}
      {hasDraft ? (
        <DraftReview
          lectures={previewLectures}
          onContinueToPublish={onContinueToPublish}
        />
      ) : null}
    </section>
  );
}

function DraftReview({
  lectures,
  onContinueToPublish,
}: {
  lectures: { id: string; label: string; previewHref: string }[];
  onContinueToPublish: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="draft-review" aria-label={t("builder.generate.review") }>
      <header>
        <strong>{t("builder.generate.review")}</strong>
        <span>{t("builder.generate.reviewHelp")}</span>
      </header>
      <div className="draft-review-list">
        {lectures.map((lecture) => (
          <div className="draft-review-row" key={lecture.id}>
            <span>{lecture.label}</span>
            <a className="button-link" href={lecture.previewHref} rel="noreferrer" target="_blank">
              {t("builder.generate.preview")}
            </a>
          </div>
        ))}
      </div>
      <button className="primary-action" type="button" onClick={onContinueToPublish}>
        {t("builder.generate.continueToPublish")}
      </button>
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
