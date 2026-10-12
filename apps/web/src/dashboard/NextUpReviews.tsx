import { CalendarPlus } from "lucide-react";
import { useState } from "react";

import { useI18n } from "../i18n/i18n";
import { calendarReviews, type NextUpReview } from "./nextUp";
import { downloadReviewCalendar } from "./reviewCalendar";
import type { CourseReviewQueue, GateReviewQueueItem, ReviewQueueItem } from "./reviewQueueTypes";
import type { Lecture } from "../shared/types";

const VISIBLE_REVIEWS = 3;

type Translator = ReturnType<typeof useI18n>["t"];

export function NextUpReviews({
  completedCount,
  queue,
  reviews,
  onOpen,
  onOpenGateReview,
}: {
  completedCount: number;
  queue: CourseReviewQueue | null;
  reviews: NextUpReview[];
  onOpen: (lecture: Lecture) => void;
  onOpenGateReview?: (item: GateReviewQueueItem) => void;
}) {
  const { t } = useI18n();
  const [exportError, setExportError] = useState<string | null>(null);
  const calendar = calendarReviews(queue);
  if (!reviews.length && !completedCount && !calendar.length) return null;
  const formatter = new Intl.DateTimeFormat(t("nextUp.dateLocale"), {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  const hidden = reviews.length - VISIBLE_REVIEWS;

  return (
    <div className="next-up-reviews">
      <div className="next-up-reviews-heading">
        <h3>{t("nextUp.reviews")}</h3>
        {completedCount ? <span>{t("nextUp.completed", { count: completedCount })}</span> : null}
        {calendar.length ? (
          <button
            className="next-up-export"
            type="button"
            onClick={() => {
              setExportError(null);
              void downloadReviewCalendar(calendar).catch((error: unknown) =>
                setExportError(
                  error instanceof Error ? error.message : t("reviewPlan.exportError"),
                ),
              );
            }}
          >
            <CalendarPlus aria-hidden="true" size={14} />
            {t("reviewPlan.export")}
          </button>
        ) : null}
      </div>
      {reviews.length ? (
        <ol className="next-up-review-list">
          {reviews.slice(0, VISIBLE_REVIEWS).map(({ item, lecture, due }) => (
            <li key={item.id}>
              <div>
                <span className={due ? "next-up-due" : "next-up-planned"}>
                  {t(due ? "reviewPlan.due" : "reviewPlan.planned")}
                </span>
                <strong>{item.section_title}</strong>
                <small>
                  {lecture.number} · {lecture.title}
                  {"due_at" in item
                    ? ` · ${formatter.format(new Date(item.due_at))} · ${t("reviewPlan.duration")}`
                    : ""}
                </small>
              </div>
              <button
                className={due ? "next-up-review-action is-due" : "next-up-review-action"}
                type="button"
                disabled={due && item.kind !== "readiness_repair" && !onOpenGateReview}
                onClick={() => {
                  if (due && item.kind !== "readiness_repair") onOpenGateReview?.(item);
                  else onOpen(lecture);
                }}
              >
                {due ? queueAction(item, t) : t("reviewPlan.open")}
              </button>
            </li>
          ))}
        </ol>
      ) : null}
      {hidden > 0 ? <p className="next-up-more">{t("nextUp.more", { count: hidden })}</p> : null}
      {exportError ? (
        <p className="form-error" role="alert">
          {exportError}
        </p>
      ) : null}
    </div>
  );
}

export function queueAction(item: ReviewQueueItem, t: Translator) {
  if (item.kind === "gate_review") return t("dashboard.recommendation.openDueReview");
  if (item.kind === "gate_repair") return t("dashboard.recommendation.openGateRepair");
  return t("dashboard.recommendation.openReadinessRepair");
}
