import { useMemo } from "react";

import { useI18n } from "./i18n";
import { courseLectureSnapshot, percent, type LectureSnapshot } from "./performanceMetrics";
import { PerformanceOverview } from "./PerformanceOverview";
import type { CourseAnalyticsSummary, Lecture } from "./types";

export function CoursePerformanceOverview({
  analytics,
  lectures,
  onSelectLecture,
}: {
  analytics: CourseAnalyticsSummary;
  lectures: Lecture[];
  onSelectLecture: (lecture: Lecture) => void;
}) {
  const { t } = useI18n();
  const rows = useMemo(() => lectureRows(analytics, lectures), [analytics, lectures]);
  const attention = rows
    .filter((row) => row.snapshot.status === "needs-attention" || row.snapshot.status === "watch")
    .sort((left, right) => statusRank(left.snapshot.status) - statusRank(right.snapshot.status));
  const coverage = rows.reduce<Record<LectureSnapshot["status"], number>>(
    (counts, row) => ({ ...counts, [row.snapshot.status]: counts[row.snapshot.status] + 1 }),
    { healthy: 0, "needs-attention": 0, "no-data": 0, watch: 0 },
  );

  return (
    <>
      <PerformanceOverview
        label={t("analytics.courseOverviewMetrics")}
        snapshot={{
          events: analytics.total_events,
          gateRate: percent(analytics.gate_rate),
          learners: analytics.unique_learners,
          quizRate: percent(analytics.quiz_rate),
          status: "no-data",
        }}
      />
      <section className="course-overview-panel">
        <header>
          <div>
            <h3>{t("analytics.focusNext")}</h3>
            <p>{t("analytics.focusNextHelp")}</p>
          </div>
          <span>
            {t("analytics.lecturesWithSignals", { count: rows.length - coverage["no-data"] })}
          </span>
        </header>
        <div className="course-overview-grid">
          <section className="attention-queue">
            <h4>{t("analytics.priorityLectures")}</h4>
            {attention.length ? (
              <div className="attention-lecture-list">
                {attention.map(({ lecture, snapshot }) => (
                  <button key={lecture.id} type="button" onClick={() => onSelectLecture(lecture)}>
                    <span className="attention-lecture-number">{lecture.number}</span>
                    <span>
                      <strong>{lecture.title}</strong>
                      <small>
                        {t("analytics.lectureSignalSummary", {
                          events: snapshot.events,
                          gate: snapshot.gateRate,
                          quiz: snapshot.quizRate,
                        })}
                      </small>
                    </span>
                    <span className={`lecture-status is-${snapshot.status}`}>
                      {statusLabel(snapshot.status, t)}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="course-overview-empty">{t("analytics.noPriorityLectures")}</p>
            )}
          </section>
          <section className="signal-coverage">
            <h4>{t("analytics.signalCoverage")}</h4>
            <dl>
              <CoverageRow
                label={t("analytics.status.attention")}
                value={coverage["needs-attention"]}
              />
              <CoverageRow label={t("analytics.status.watch")} value={coverage.watch} />
              <CoverageRow label={t("analytics.status.healthy")} value={coverage.healthy} />
              <CoverageRow label={t("analytics.status.noData")} value={coverage["no-data"]} />
            </dl>
          </section>
        </div>
      </section>
    </>
  );
}

function CoverageRow({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function lectureRows(analytics: CourseAnalyticsSummary, lectures: Lecture[]) {
  const byId = new Map(analytics.lectures.map((lecture) => [lecture.lecture_id, lecture]));
  return lectures.map((lecture) => {
    const rollup = byId.get(lecture.id);
    return {
      lecture,
      snapshot: rollup
        ? courseLectureSnapshot(rollup)
        : { events: 0, gateRate: "n/a", learners: 0, quizRate: "n/a", status: "no-data" as const },
    };
  });
}

function statusRank(status: LectureSnapshot["status"]) {
  if (status === "needs-attention") return 0;
  if (status === "watch") return 1;
  return 2;
}

function statusLabel(status: LectureSnapshot["status"], t: ReturnType<typeof useI18n>["t"]) {
  if (status === "needs-attention") return t("analytics.status.attention");
  if (status === "watch") return t("analytics.status.watch");
  if (status === "healthy") return t("analytics.status.healthy");
  return t("analytics.status.noData");
}
