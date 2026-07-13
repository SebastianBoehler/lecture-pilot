import { useI18n } from "./i18n";
import type { LectureSnapshot } from "./performanceMetrics";
import type { Lecture } from "./types";

export function PerformanceLectureRow({
  active,
  lecture,
  onSelect,
  snapshot,
}: {
  active: boolean;
  lecture: Lecture;
  onSelect: () => void;
  snapshot: LectureSnapshot | null;
}) {
  const { t } = useI18n();
  return (
    <button
      aria-current={active ? "true" : undefined}
      aria-pressed={active}
      className={active ? "is-active" : undefined}
      type="button"
      onClick={onSelect}
    >
      <span className="lecture-index">{lecture.number}</span>
      <span className="lecture-row-body">
        <strong>{lecture.title}</strong>
        <small>{lecture.date}</small>
        {active && snapshot ? (
          <span className={`lecture-status is-${snapshot.status}`}>
            {statusLabel(snapshot.status, t)}
          </span>
        ) : null}
      </span>
    </button>
  );
}

function statusLabel(status: LectureSnapshot["status"], t: ReturnType<typeof useI18n>["t"]) {
  if (status === "healthy") return t("analytics.status.healthy");
  if (status === "watch") return t("analytics.status.watch");
  if (status === "needs-attention") return t("analytics.status.attention");
  return t("analytics.status.noData");
}
