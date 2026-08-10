import { useEffect, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import { ProfessorLearningDesignReview } from "./ProfessorLearningDesignReview";

type PreviewLecture = { id: string; label: string; previewHref: string };
type ReviewView = "preview" | "design";

export function ProfessorCanvasReviewWorkspace({
  canContinue,
  lectures,
  learningDesignReviews,
  learningDesignAcknowledgementKey,
  learningDesignSaving,
  onApproveLearningDesign,
  onContinueToPublish,
  onSaveLearningDesign,
}: {
  canContinue: boolean;
  lectures: PreviewLecture[];
  learningDesignReviews: Record<string, LearningDesignReview>;
  learningDesignAcknowledgementKey: string;
  learningDesignSaving: boolean;
  onApproveLearningDesign: (lectureId: string, acknowledgedWarningIds: string[]) => void;
  onContinueToPublish: () => void;
  onSaveLearningDesign: (lectureId: string, update: LearningDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const [selectedId, setSelectedId] = useState(lectures[0]?.id ?? "");
  const [view, setView] = useState<ReviewView>("preview");
  const selected = lectures.find((lecture) => lecture.id === selectedId) ?? lectures[0];
  const review = selected ? learningDesignReviews[selected.id] : undefined;
  const approvedCount = useMemo(
    () => lectures.filter((lecture) => learningDesignReviews[lecture.id]?.approval).length,
    [lectures, learningDesignReviews],
  );
  useEffect(() => {
    if (selectedId && lectures.some((lecture) => lecture.id === selectedId)) return;
    setSelectedId(lectures[0]?.id ?? "");
  }, [lectures, selectedId]);

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
      <nav aria-label={t("builder.generate.lectureSelector")} className="draft-review-lectures">
        {lectures.map((lecture) => {
          const approved = Boolean(learningDesignReviews[lecture.id]?.approval);
          return (
            <button
              aria-label={lecture.label}
              aria-pressed={lecture.id === selected?.id}
              key={lecture.id}
              type="button"
              onClick={() => {
                setSelectedId(lecture.id);
                setView("preview");
              }}
            >
              <span>{lecture.label}</span>
              <small>
                {t(
                  approved
                    ? "builder.generate.reviewStatus.approved"
                    : "builder.generate.reviewStatus.pending",
                )}
              </small>
            </button>
          );
        })}
      </nav>
      {selected ? (
        <article className="draft-review-workspace">
          <header className="draft-review-selected-header">
            <div>
              <small>{t("builder.generate.selectedLecture")}</small>
              <h3>{selected.label}</h3>
            </div>
            <a className="button-link" href={selected.previewHref} rel="noreferrer" target="_blank">
              {t("builder.generate.openPreview")}
            </a>
          </header>
          <div aria-label={t("builder.generate.reviewViews")} className="draft-review-tabs">
            <button
              aria-pressed={view === "preview"}
              type="button"
              onClick={() => setView("preview")}
            >
              {t("builder.generate.viewPreview")}
            </button>
            <button
              aria-pressed={view === "design"}
              type="button"
              onClick={() => setView("design")}
            >
              {t("builder.generate.viewDesign")}
            </button>
          </div>
          {view === "preview" ? (
            <div className="learner-preview-frame">
              <p>{t("builder.generate.previewHelp")}</p>
              <iframe src={selected.previewHref} title={t("builder.learningDesign.preview")} />
            </div>
          ) : review ? (
            <ProfessorLearningDesignReview
              acknowledgementResetKey={learningDesignAcknowledgementKey}
              lectureId={selected.id}
              review={review}
              saving={learningDesignSaving}
              onApprove={onApproveLearningDesign}
              onSave={onSaveLearningDesign}
            />
          ) : (
            <p role="status">{t("builder.learningDesign.loading")}</p>
          )}
        </article>
      ) : null}
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
