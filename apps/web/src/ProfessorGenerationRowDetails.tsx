import { useI18n } from "./i18n";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";

export function ProfessorGenerationRowDetails({
  progress,
  retrying,
  onRetry,
  onReviewLearningGoals,
}: {
  progress: CanvasGenerationProgress;
  retrying: boolean;
  onRetry?: (lectureId: string) => void;
  onReviewLearningGoals?: () => void;
}) {
  const { t } = useI18n();
  if (progress.status !== "error") return null;
  const repair = progress.errorKind === "repair";
  const design = progress.errorKind === "design";
  const message =
    progress.errorKind === "network"
      ? t("builder.generate.error.network")
      : t(repair ? "builder.generate.error.repair" : "builder.generate.error.service", {
          message: progress.message ?? t("builder.generate.error.unknown"),
        });
  return (
    <div className="generation-progress-row is-error">
      <button
        aria-label={
          design
            ? t("builder.generate.reviewGoals")
            : t(repair ? "builder.generate.repairLecture" : "builder.generate.retryLecture", {
                lecture: progress.lectureId.replace("lecture-", "Lecture "),
              })
        }
        disabled={retrying || (design && !onReviewLearningGoals)}
        type="button"
        onClick={() => (design ? onReviewLearningGoals?.() : onRetry?.(progress.lectureId))}
      >
        {t(
          design
            ? "builder.generate.reviewGoals"
            : repair
              ? "builder.generate.repair"
              : "builder.generate.retry",
        )}
      </button>
      {design ? <p role="alert">{t("builder.generate.goalConflict")}</p> : null}
      <details className="generation-error-details">
        <summary>{t("builder.generate.failureDetails")}</summary>
        <small>{message}</small>
      </details>
    </div>
  );
}
