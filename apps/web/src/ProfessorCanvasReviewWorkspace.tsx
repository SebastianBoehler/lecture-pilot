import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "./i18n";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import { ProfessorLearningDesignReview } from "./ProfessorLearningDesignReview";

type PreviewLecture = { id: string; label: string; previewHref: string };

export function ProfessorCanvasReviewWorkspace({
  canContinue,
  lectures,
  learningDesignReviews,
  learningDesignSaving,
  onApproveLearningDesign,
  onContinueToPublish,
  onSaveLearningDesign,
}: {
  canContinue: boolean;
  lectures: PreviewLecture[];
  learningDesignReviews: Record<string, LearningDesignReview>;
  learningDesignSaving: boolean;
  onApproveLearningDesign: (lectureId: string) => void;
  onContinueToPublish: () => void;
  onSaveLearningDesign: (lectureId: string, update: LearningDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const [openDesignId, setOpenDesignId] = useState("");
  const pendingApprovalId = useRef("");
  const approvedCount = useMemo(
    () => lectures.filter((lecture) => learningDesignReviews[lecture.id]?.approval).length,
    [lectures, learningDesignReviews],
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
      <ul className="draft-review-list">
        {lectures.map((lecture) => {
          const approved = Boolean(learningDesignReviews[lecture.id]?.approval);
          const designOpen = openDesignId === lecture.id;
          const review = learningDesignReviews[lecture.id];
          const panelId = `learning-design-${lecture.id}`;
          return (
            <li className={designOpen ? "is-open" : undefined} key={lecture.id}>
              <div className="draft-review-row">
                <div>
                  <strong>{lecture.label}</strong>
                  <small>
                    {t(
                      approved
                        ? "builder.generate.reviewStatus.approved"
                        : "builder.generate.reviewStatus.pending",
                    )}
                  </small>
                </div>
                <div className="draft-review-actions">
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
                      designOpen ? "builder.generate.closeDesign" : "builder.generate.reviewDesign",
                    )}
                  </button>
                </div>
              </div>
              {designOpen ? (
                <div className="draft-design-panel" id={panelId}>
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
                  ) : (
                    <p role="status">{t("builder.learningDesign.loading")}</p>
                  )}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
      <footer className="draft-review-footer">
        <span>{t("builder.generate.publishGateHelp")}</span>
        <button
          className="primary-action"
          disabled={!canContinue}
          type="button"
          onClick={onContinueToPublish}
        >
          {t("builder.generate.continueToPublish")}
        </button>
      </footer>
    </section>
  );
}
