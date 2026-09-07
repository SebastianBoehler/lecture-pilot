import type { ReactNode } from "react";
import { useI18n } from "./i18n";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import { ProfessorCanvasReviewWorkspace } from "./ProfessorCanvasReviewWorkspace";
import { PendingStatus } from "./ProfessorCourseBuilderParts";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import type { CanvasDocument } from "./types";

export function ProfessorCanvasDraftStep({
  canvas,
  publicationAction,
  canGenerate,
  generationProgress,
  generatedCount,
  isFullCourse,
  isGenerating,
  learningDesignReviews,
  learningDesignSaving,
  learningDesignErrors = {},
  onReloadLearningDesign,
  onApproveLearningDesign,
  onGenerate,
  onRetry,
  onSaveLearningDesign,
  renderImplementationChanges,
  previewLectures,
  lectures,
  renderPublishedLecture,
  retryingLectureIds = new Set(),
  totalCount,
}: {
  canvas: CanvasDocument | null;
  publicationAction?: ReactNode;
  canGenerate: boolean;
  generationProgress: CanvasGenerationProgress[];
  generatedCount: number;
  isFullCourse: boolean;
  isGenerating: boolean;
  learningDesignReviews: Record<string, LearningDesignReview>;
  learningDesignSaving: boolean;
  learningDesignErrors?: Readonly<Record<string, string>>;
  onReloadLearningDesign?: (lectureId: string) => void;
  onApproveLearningDesign: (lectureId: string) => void;
  onGenerate: () => void;
  onRetry: (lectureId: string) => void;
  onSaveLearningDesign: (lectureId: string, update: LearningDesignUpdate) => void;
  renderImplementationChanges?: (lectureId: string) => ReactNode;
  previewLectures: {
    id: string;
    label: string;
    previewHref: string;
  }[];
  lectures?: { id: string; label: string; previewHref: string; published: boolean }[];
  renderPublishedLecture?: (lectureId: string) => ReactNode;
  retryingLectureIds?: ReadonlySet<string>;
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
  const hasUnfinished = generationProgress.some((item) => item.status === "error");
  const timeEstimate = isFullCourse
    ? t("builder.generate.estimateAll", {
        count: totalCount,
      })
    : t("builder.generate.estimateSingle");
  return (
    <section className="flow-card">
      {!hasDraft || isGenerating ? (
        <aside aria-label={t("builder.generate.timingLabel")} className="generation-time-notice">
          <strong>{timeEstimate}</strong>
          <span>{t("builder.generate.backgroundHelp")}</span>
        </aside>
      ) : null}
      <details className="builder-optional" open={!hasDraft || hasUnfinished || isGenerating}>
        <summary>{t("builder.generate.title")}</summary>
        <button
          className={hasDraft ? undefined : "primary-action"}
          disabled={!canGenerate || isGenerating}
          type="button"
          onClick={onGenerate}
        >
          {isGenerating
            ? busyLabel
            : hasUnfinished
              ? t("builder.generate.resume")
              : hasDraft
                ? t("builder.generate.regenerate")
                : actionLabel}
        </button>
        {isGenerating ? <PendingStatus label={statusLabel} /> : null}
      </details>
      {hasDraft && isFullCourse ? (
        <p>{t("builder.generate.fullReady", { count: generatedCount })}</p>
      ) : null}
      {publicationAction}
      <ProfessorCanvasReviewWorkspace
        lectures={
          lectures ?? [
            ...previewLectures,
            ...generationProgress
              .filter((item) => !previewLectures.some((lecture) => lecture.id === item.lectureId))
              .map((item) => ({
                id: item.lectureId,
                label: item.lectureId.replace("lecture-", "Lecture "),
                previewHref: "",
              })),
          ]
        }
        generationProgress={generationProgress}
        retryingLectureIds={retryingLectureIds}
        onRetry={onRetry}
        renderPublishedLecture={renderPublishedLecture}
        learningDesignReviews={learningDesignReviews}
        learningDesignSaving={learningDesignSaving}
        learningDesignErrors={learningDesignErrors}
        onReloadLearningDesign={onReloadLearningDesign}
        onApproveLearningDesign={onApproveLearningDesign}
        onSaveLearningDesign={onSaveLearningDesign}
        renderImplementationChanges={renderImplementationChanges}
      />
    </section>
  );
}
