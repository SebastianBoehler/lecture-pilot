import { useI18n } from "./i18n";
import type { GateReviewQueueItem } from "./reviewQueueTypes";
import type { Lecture } from "./types";

export function DashboardUpcomingReviews({
  items,
  lectures,
  onOpen,
}: {
  items: GateReviewQueueItem[];
  lectures: Lecture[];
  onOpen: (lecture: Lecture) => void;
}) {
  const { locale, t } = useI18n();
  const available = items.flatMap((item) => {
    const lecture = lectures.find((candidate) => candidate.id === item.lecture_id);
    return lecture ? [{ item, lecture }] : [];
  });
  if (!available.length) return null;

  const formatter = new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <section className="course-panel upcoming-reviews" aria-labelledby="upcoming-reviews-heading">
      <div className="panel-heading">
        <h2 id="upcoming-reviews-heading">{t("dashboard.upcomingReviews.title")}</h2>
      </div>
      <ul>
        {available.map(({ item, lecture }) => (
          <li key={item.id}>
            <div>
              <strong>{item.section_title}</strong>
              <span>{item.lecture_title}</span>
              <time dateTime={item.due_at}>
                {t("dashboard.upcomingReviews.due", {
                  date: formatter.format(new Date(item.due_at)),
                })}
              </time>
            </div>
            <button
              type="button"
              aria-label={t("dashboard.upcomingReviews.openLectureFor", {
                section: item.section_title,
              })}
              onClick={() => onOpen(lecture)}
            >
              {t("dashboard.upcomingReviews.openLecture")}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
