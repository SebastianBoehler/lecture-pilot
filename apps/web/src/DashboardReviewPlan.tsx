import { useState } from "react";
import { useI18n } from "./i18n";
import { downloadReviewCalendar } from "./reviewCalendar";
import type { CourseReviewQueue, GateReviewQueueItem } from "./reviewQueueTypes";
import type { Lecture } from "./types";

export function DashboardReviewPlan({
  queue,
  lectures,
  onOpen,
  onOpenDue,
}: {
  queue: CourseReviewQueue | null;
  lectures: Lecture[];
  onOpen: (lecture: Lecture) => void;
  onOpenDue: (item: GateReviewQueueItem) => void;
}) {
  const { locale, t } = useI18n();
  const [exportError, setExportError] = useState<string | null>(null);
  if (!queue) return null;
  const due = queue.items.filter(
    (item): item is GateReviewQueueItem => item.kind === "gate_review",
  );
  const upcoming = queue.upcoming;
  const completed = queue.completed ?? [];
  if (!due.length && !upcoming.length && !completed.length) return null;
  const formatter = new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <section className="course-panel review-plan" aria-labelledby="review-plan-heading">
      <div className="review-plan-heading">
        <div>
          <h2 id="review-plan-heading">{t("reviewPlan.title")}</h2>
          <p>
            {t("reviewPlan.summary", {
              pending: String(due.length + upcoming.length),
              completed: String(completed.length),
            })}
          </p>
        </div>
        {due.length + upcoming.length > 0 ? (
          <button
            className="review-plan-export"
            type="button"
            onClick={() => {
              setExportError(null);
              void downloadReviewCalendar([...due, ...upcoming]).catch((error: unknown) =>
                setExportError(
                  error instanceof Error ? error.message : t("reviewPlan.exportError"),
                ),
              );
            }}
          >
            {t("reviewPlan.export")}
          </button>
        ) : null}
      </div>
      <ol className="review-plan-list">
        {[...due, ...upcoming].map((item) => {
          const lecture = lectures.find((candidate) => candidate.id === item.lecture_id);
          if (!lecture) return null;
          const isDue = due.includes(item);
          return (
            <li key={item.id}>
              <div>
                <span className={isDue ? "review-plan-due" : "review-plan-upcoming"}>
                  {t(isDue ? "reviewPlan.due" : "reviewPlan.planned")}
                </span>
                <strong>{item.section_title}</strong>
                <small>
                  {formatter.format(new Date(item.due_at))} · {t("reviewPlan.duration")}
                </small>
              </div>
              <button
                className={isDue ? "review-plan-action is-due" : "review-plan-action"}
                type="button"
                onClick={() => (isDue ? onOpenDue(item) : onOpen(lecture))}
              >
                {t(isDue ? "reviewPlan.start" : "reviewPlan.open")}
              </button>
            </li>
          );
        })}
        {completed.map((item) => (
          <li key={item.id} className="review-plan-completed">
            <div>
              <span>{t("reviewPlan.completed")}</span>
              <strong>{item.section_title}</strong>
              <small>{formatter.format(new Date(item.completed_at))}</small>
            </div>
          </li>
        ))}
      </ol>
      {exportError ? (
        <p className="form-error" role="alert">
          {exportError}
        </p>
      ) : null}
    </section>
  );
}
