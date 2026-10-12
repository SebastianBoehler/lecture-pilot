import { useI18n } from "../i18n/i18n";
import { bestNextAction, remainingReviews, type LectureReason, type NextUpAction } from "./nextUp";
import { NextUpReviews, queueAction } from "./NextUpReviews";
import type { CourseReviewQueue, GateReviewQueueItem } from "./reviewQueueTypes";
import type { Lecture, UniversityCourse } from "../shared/types";

type Translator = ReturnType<typeof useI18n>["t"];

/** One card for the best next action plus a short list of due and planned reviews. */
export function NextUpCard({
  course,
  lectures,
  passedLectureIds,
  reviewQueue = null,
  onOpen,
  onOpenGateReview,
}: {
  course: UniversityCourse;
  lectures: Lecture[];
  passedLectureIds: string[];
  reviewQueue?: CourseReviewQueue | null;
  onOpen: (lecture: Lecture) => void;
  onOpenGateReview?: (item: GateReviewQueueItem) => void;
}) {
  const { t } = useI18n();
  const primary = bestNextAction(lectures, passedLectureIds, reviewQueue);
  const reviews = remainingReviews(lectures, reviewQueue, primary);
  if (!primary) return null;

  return (
    <section className="next-up" aria-labelledby="next-up-heading">
      <div className="next-up-primary">
        <div>
          <h2 id="next-up-heading">{t("nextUp.title")}</h2>
          <p>{primaryReason(primary, t)}</p>
        </div>
        <div className="next-up-action">
          <span className="next-up-course">{course.title}</span>
          <strong>
            {primary.kind === "queue"
              ? primary.item.section_title
              : `${primary.lecture.number} · ${primary.lecture.title}`}
          </strong>
          <PrimaryButton
            action={primary}
            course={course}
            onOpen={onOpen}
            onOpenGateReview={onOpenGateReview}
          />
        </div>
      </div>
      <NextUpReviews
        completedCount={reviewQueue?.completed?.length ?? 0}
        queue={reviewQueue}
        reviews={reviews}
        onOpen={onOpen}
        onOpenGateReview={onOpenGateReview}
      />
    </section>
  );
}

function PrimaryButton({
  action,
  course,
  onOpen,
  onOpenGateReview,
}: {
  action: NextUpAction;
  course: UniversityCourse;
  onOpen: (lecture: Lecture) => void;
  onOpenGateReview?: (item: GateReviewQueueItem) => void;
}) {
  const { t } = useI18n();
  if (action.kind === "lecture") {
    return (
      <button
        aria-label={t("dashboard.recommendation.openForCourse", {
          course: course.title,
          number: action.lecture.number,
        })}
        type="button"
        onClick={() => onOpen(action.lecture)}
      >
        {t("dashboard.recommendation.open")}
      </button>
    );
  }
  const item = action.item;
  return (
    <button
      disabled={item.kind !== "readiness_repair" && !onOpenGateReview}
      type="button"
      onClick={() => {
        if (item.kind === "readiness_repair") onOpen(action.lecture);
        else onOpenGateReview?.(item);
      }}
    >
      {queueAction(item, t)}
    </button>
  );
}

function primaryReason(action: NextUpAction, t: Translator) {
  if (action.kind === "lecture") return lectureReason(action.reason, t);
  if (action.item.kind === "readiness_repair") return action.item.next_action;
  if (action.item.kind === "gate_review") return t("dashboard.recommendation.dueReview");
  return t("dashboard.recommendation.gateRepair");
}

function lectureReason(kind: LectureReason, t: Translator) {
  if (kind === "missed") return t("dashboard.recommendation.missed");
  if (kind === "diagnostic") return t("dashboard.recommendation.diagnostic");
  if (kind === "review") return t("dashboard.recommendation.review");
  return t("dashboard.recommendation.continue");
}
