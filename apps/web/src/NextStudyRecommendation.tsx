import type { ReactNode } from "react";

import { useI18n } from "./i18n";
import type { CourseReviewQueue, GateReviewQueueItem, ReviewQueueItem } from "./reviewQueueTypes";
import type { Lecture, UniversityCourse } from "./types";

export function NextStudyRecommendation({
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
  const queueItem = reviewQueue?.items[0];
  const queuedLecture = queueItem
    ? lectures.find((lecture) => lecture.id === queueItem.lecture_id)
    : undefined;
  if (queueItem && queuedLecture) {
    return (
      <RecommendationShell course={course} label={queueItem.section_title}>
        <p>{queueReason(queueItem, t)}</p>
        <button
          aria-label={queueAction(queueItem, t)}
          disabled={queueItem.kind !== "readiness_repair" && !onOpenGateReview}
          type="button"
          onClick={() => {
            if (queueItem.kind === "readiness_repair") onOpen(queuedLecture);
            else onOpenGateReview?.(queueItem);
          }}
        >
          {queueAction(queueItem, t)}
        </button>
      </RecommendationShell>
    );
  }
  const recommendation = recommendLecture(lectures, passedLectureIds);
  if (!recommendation) return null;

  return (
    <RecommendationShell
      course={course}
      label={`${recommendation.lecture.number} · ${recommendation.lecture.title}`}
    >
      <p>{reason(recommendation.reason, t)}</p>
      <button
        aria-label={t("dashboard.recommendation.openForCourse", {
          course: course.title,
          number: recommendation.lecture.number,
        })}
        type="button"
        onClick={() => onOpen(recommendation.lecture)}
      >
        {t("dashboard.recommendation.open")}
      </button>
    </RecommendationShell>
  );
}

function RecommendationShell({
  children,
  course,
  label,
}: {
  children: ReactNode;
  course: UniversityCourse;
  label: string;
}) {
  const { t } = useI18n();
  const parts = Array.isArray(children) ? children : [children];
  return (
    <section className="next-study" aria-labelledby="next-study-heading">
      <div>
        <h2 id="next-study-heading">{t("dashboard.recommendation.title")}</h2>
        {parts[0]}
      </div>
      <div className="next-study-action">
        <span className="next-study-course">{course.title}</span>
        <strong>{label}</strong>
        {parts.slice(1)}
      </div>
    </section>
  );
}

export function recommendLecture(lectures: Lecture[], passedLectureIds: string[]) {
  if (!lectures.length) return null;
  const passed = new Set(passedLectureIds);
  const incomplete = lectures.filter((lecture) => !passed.has(lecture.id));
  const missed = incomplete.find((lecture) => lecture.attendance === "absent");
  if (missed) return { lecture: missed, reason: "missed" as const };
  const diagnostic = incomplete.find((lecture) => lecture.attendance === "unknown");
  if (diagnostic) return { lecture: diagnostic, reason: "diagnostic" as const };
  if (incomplete[0]) return { lecture: incomplete[0], reason: "continue" as const };
  return { lecture: lectures.at(-1)!, reason: "review" as const };
}

function reason(
  kind: "missed" | "diagnostic" | "continue" | "review",
  t: ReturnType<typeof useI18n>["t"],
) {
  if (kind === "missed") return t("dashboard.recommendation.missed");
  if (kind === "diagnostic") return t("dashboard.recommendation.diagnostic");
  if (kind === "review") return t("dashboard.recommendation.review");
  return t("dashboard.recommendation.continue");
}

function queueReason(item: ReviewQueueItem, t: ReturnType<typeof useI18n>["t"]) {
  if (item.kind === "readiness_repair") return item.next_action;
  if (item.kind === "gate_review") return t("dashboard.recommendation.dueReview");
  return t("dashboard.recommendation.gateRepair");
}

function queueAction(item: ReviewQueueItem, t: ReturnType<typeof useI18n>["t"]) {
  if (item.kind === "gate_review") return t("dashboard.recommendation.openDueReview");
  if (item.kind === "gate_repair") return t("dashboard.recommendation.openGateRepair");
  return t("dashboard.recommendation.openReadinessRepair");
}
