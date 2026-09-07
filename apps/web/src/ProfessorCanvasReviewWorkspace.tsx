import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "./i18n";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import { ProfessorGenerationRowDetails } from "./ProfessorGenerationRowDetails";
import { ProfessorLearningDesignReview } from "./ProfessorLearningDesignReview";
import { ProfessorLectureStatus } from "./ProfessorLectureStatus";

type PreviewLecture = { id: string; label: string; previewHref: string; published?: boolean };

export function ProfessorCanvasReviewWorkspace({
  lectures,
  generationProgress = [],
  retryingLectureIds = new Set(),
  onRetry,
  renderPublishedLecture,
  learningDesignReviews,
  learningDesignSaving,
  learningDesignErrors = {},
  onReloadLearningDesign,
  onApproveLearningDesign,
  onSaveLearningDesign,
  renderImplementationChanges,
}: {
  lectures: PreviewLecture[];
  generationProgress?: CanvasGenerationProgress[];
  retryingLectureIds?: ReadonlySet<string>;
  onRetry?: (lectureId: string) => void;
  renderPublishedLecture?: (lectureId: string) => ReactNode;
  learningDesignReviews: Record<string, LearningDesignReview>;
  learningDesignSaving: boolean;
  learningDesignErrors?: Readonly<Record<string, string>>;
  onReloadLearningDesign?: (lectureId: string) => void;
  onApproveLearningDesign: (lectureId: string) => void;
  onSaveLearningDesign: (lectureId: string, update: LearningDesignUpdate) => void;
  renderImplementationChanges?: (lectureId: string) => ReactNode;
}) {
  const { t } = useI18n();
  const [openDesignId, setOpenDesignId] = useState("");
  const pendingApprovalId = useRef("");
  const approvedCount = useMemo(
    () =>
      lectures.filter(
        (lecture) =>
          learningDesignReviews[lecture.id]?.approval &&
          !generationProgress.some(
            (item) => item.lectureId === lecture.id && item.status !== "ready",
          ),
      ).length,
    [lectures, learningDesignReviews, generationProgress],
  );
  useEffect(() => {
    const lectureId = pendingApprovalId.current;
    if (!lectureId || !learningDesignReviews[lectureId]?.approval) return;
    setOpenDesignId((current) => (current === lectureId ? "" : current));
    pendingApprovalId.current = "";
  }, [learningDesignReviews]);

  return (
    <section className="draft-review" aria-label={t("builder.generate.review")}>
      <header className="draft-review-header">
        <div>
          <strong>{t("builder.generate.review")}</strong>
          <span>{t("builder.generate.reviewHelp")}</span>
        </div>
        <span className="draft-review-progress">
          {t("builder.generate.reviewProgress", {
            approved: approvedCount,
            total: lectures.length,
          })}
        </span>
      </header>
      {generationProgress.some((item) => item.status === "error") ? (
        <p className="generation-progress-context">{t("builder.generate.previousRunHelp")}</p>
      ) : null}
      <ul className="draft-review-list" aria-label={t("builder.generate.progress")}>
        {lectures.map((lecture) => {
          const approved = Boolean(learningDesignReviews[lecture.id]?.approval);
          const designOpen = openDesignId === lecture.id;
          const review = learningDesignReviews[lecture.id];
          const progress = generationProgress.find((item) => item.lectureId === lecture.id);
          const blocked = progress && progress.status !== "ready";
          const hasDraft =
            !blocked &&
            Boolean(lecture.previewHref) &&
            (Boolean(review) || progress?.status === "ready" || Boolean(lecture.published));
          const panelId = `learning-design-${lecture.id}`;
          return (
            <li className={designOpen ? "is-open" : undefined} key={lecture.id}>
              <div className="draft-review-row">
                <div>
                  <strong>{lecture.label}</strong>
                  <ProfessorLectureStatus
                    state={
                      retryingLectureIds.has(lecture.id)
                        ? "generating"
                        : progress && progress.status !== "ready"
                          ? progress.status
                          : lecture.published && approved
                            ? "published"
                            : !hasDraft
                              ? "pending"
                              : approved
                                ? "approved"
                                : "review"
                    }
                  />
                </div>
                <div className="draft-review-actions">
                  {hasDraft ? (
                    <a
                      aria-label={t("builder.generate.openPreviewLecture", {
                        lecture: lecture.label,
                      })}
                      className="button-link"
                      href={lecture.previewHref}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {t("builder.generate.openPreview")}
                    </a>
                  ) : null}
                  {hasDraft ? (
                    <button
                      aria-controls={panelId}
                      aria-expanded={designOpen}
                      aria-label={t(
                        designOpen
                          ? "builder.generate.closeDesignLecture"
                          : "builder.generate.reviewDesignLecture",
                        { lecture: lecture.label },
                      )}
                      type="button"
                      onClick={() => setOpenDesignId(designOpen ? "" : lecture.id)}
                    >
                      {t(
                        designOpen
                          ? "builder.generate.closeDesign"
                          : "builder.generate.reviewDesign",
                      )}
                    </button>
                  ) : null}
                </div>
              </div>
              {progress ? (
                <ProfessorGenerationRowDetails
                  progress={progress}
                  retrying={retryingLectureIds.has(lecture.id)}
                  onRetry={onRetry}
                />
              ) : null}
              {designOpen && hasDraft ? (
                <div className="draft-design-panel" id={panelId}>
                  {learningDesignErrors[lecture.id] ? (
                    <div>
                      <p className="form-error" role="alert">
                        {learningDesignErrors[lecture.id]}
                      </p>
                      <button type="button" onClick={() => onReloadLearningDesign?.(lecture.id)}>
                        {t("builder.learningDesign.retry")}
                      </button>
                    </div>
                  ) : null}
                  {review ? (
                    <ProfessorLearningDesignReview
                      lectureId={lecture.id}
                      review={review}
                      saving={learningDesignSaving}
                      onApprove={(lectureId) => {
                        pendingApprovalId.current = lectureId;
                        onApproveLearningDesign(lectureId);
                      }}
                      onSave={onSaveLearningDesign}
                    />
                  ) : !learningDesignErrors[lecture.id] ? (
                    <p role="status">{t("builder.learningDesign.loading")}</p>
                  ) : null}
                  {renderImplementationChanges?.(lecture.id)}
                  {lecture.published ? renderPublishedLecture?.(lecture.id) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
