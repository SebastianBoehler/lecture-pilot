import { useI18n } from "./i18n";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";

export function ProfessorGenerationRowDetails({
  progress,
  retrying,
  onRetry,
}: {
  progress: CanvasGenerationProgress;
  retrying: boolean;
  onRetry?: (lectureId: string) => void;
}) {
  const { t } = useI18n();
  if (progress.status !== "error") return null;
  const repair = progress.errorKind === "repair";
  const message =
    progress.errorKind === "network"
      ? t("builder.generate.error.network")
      : t(repair ? "builder.generate.error.repair" : "builder.generate.error.service", {
          message: progress.message ?? t("builder.generate.error.unknown"),
        });
  return (
    <div className="generation-progress-row is-error">
      <button
        aria-label={t(repair ? "builder.generate.repairLecture" : "builder.generate.retryLecture", {
          lecture: progress.lectureId.replace("lecture-", "Lecture "),
        })}
        disabled={retrying}
        type="button"
        onClick={() => onRetry?.(progress.lectureId)}
      >
        {t(repair ? "builder.generate.repair" : "builder.generate.retry")}
      </button>
      <details className="generation-error-details">
        <summary>{t("builder.generate.failureDetails")}</summary>
        <small>{message}</small>
      </details>
    </div>
  );
}
