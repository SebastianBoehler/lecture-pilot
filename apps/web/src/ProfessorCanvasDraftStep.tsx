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
  onRetry,
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
  onRetry: (lectureId: string) => void;
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
  const activeCount = generationProgress.filter(
    (item) => item.status === "pending" || item.status === "generating",
  ).length;
  const statusLabel =
    isFullCourse && activeCount !== 1
      ? t("builder.generate.statusAll", { count: activeCount || totalCount })
      : t("builder.generate.statusSingle");
  const hasDraft = Boolean(canvas);
  const allDraftsReady =
    generationProgress.length === 0 || generationProgress.every((item) => item.status === "ready");
  return (
    <section className="flow-card">
      <StepHeader
        number="04"
        title={t("builder.generate.title")}
        done={hasDraft && allDraftsReady}
      />
      <button
        className={hasDraft ? undefined : "primary-action"}
        disabled={!canGenerate || isGenerating}
        type="button"
        onClick={onGenerate}
      >
        {isGenerating ? busyLabel : hasDraft ? t("builder.generate.regenerate") : actionLabel}
      </button>
      {isGenerating ? <PendingStatus label={statusLabel} /> : null}
      {generationProgress.length ? (
        <GenerationProgressList
          isGenerating={isGenerating}
          onRetry={onRetry}
          progress={generationProgress}
        />
      ) : null}
      {hasDraft && isFullCourse ? (
        <p>{t("builder.generate.fullReady", { count: generatedCount })}</p>
      ) : null}
      {canvas && !isFullCourse ? (
        <p>{t("builder.generate.singleReady", { count: canvas.sections.length })}</p>
      ) : null}
      {hasDraft ? (
        <DraftReview
          canContinue={allDraftsReady}
          lectures={previewLectures}
          onContinueToPublish={onContinueToPublish}
        />
      ) : null}
    </section>
  );
}

function DraftReview({
  canContinue,
  lectures,
  onContinueToPublish,
}: {
  canContinue: boolean;
  lectures: { id: string; label: string; previewHref: string }[];
  onContinueToPublish: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="draft-review" aria-label={t("builder.generate.review")}>
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
      <button
        className="primary-action"
        disabled={!canContinue}
        type="button"
        onClick={onContinueToPublish}
      >
        {t("builder.generate.continueToPublish")}
      </button>
    </section>
  );
}

function GenerationProgressList({
  isGenerating,
  onRetry,
  progress,
}: {
  isGenerating: boolean;
  onRetry: (lectureId: string) => void;
  progress: CanvasGenerationProgress[];
}) {
  const { t } = useI18n();
  return (
    <div
      aria-label={t("builder.generate.progress")}
      aria-live="polite"
      className="generation-progress"
    >
      {progress.map((item) => {
        const lectureLabel = item.lectureId.replace("lecture-", "Lecture ");
        const canRepair = item.errorKind === "repair";
        const message =
          item.status === "error"
            ? item.errorKind === "network"
              ? t("builder.generate.error.network")
              : t(canRepair ? "builder.generate.error.repair" : "builder.generate.error.service", {
                  message: item.message ?? t("builder.generate.error.unknown"),
                })
            : item.message;
        return (
          <div className={`generation-progress-row is-${item.status}`} key={item.lectureId}>
            <span>{lectureLabel}</span>
            <strong>{item.status}</strong>
            {item.status === "error" ? (
              <button
                aria-label={t(
                  canRepair ? "builder.generate.repairLecture" : "builder.generate.retryLecture",
                  { lecture: lectureLabel },
                )}
                disabled={isGenerating}
                type="button"
                onClick={() => onRetry(item.lectureId)}
              >
                {t(canRepair ? "builder.generate.repair" : "builder.generate.retry")}
              </button>
            ) : null}
            {message ? <small>{message}</small> : null}
          </div>
        );
      })}
    </div>
  );
}
