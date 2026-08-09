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
  const coverage = rows.reduce<Record<LectureSnapshot["status"], number>>(
    (counts, row) => ({ ...counts, [row.snapshot.status]: counts[row.snapshot.status] + 1 }),
    { available: 0, "insufficient-data": 0, "historical-only": 0, "no-data": 0 },
  );

  return (
    <>
      <PerformanceOverview
        label={t("analytics.courseOverviewMetrics")}
        snapshot={{
          events: analytics.activity_events,
          gateEvidence: analytics.independent_first_pass,
          gateRate: percent(analytics.independent_first_pass.rate),
          learners: analytics.unique_learners,
          learningMapRevision: null,
          publicationVersion: null,
          quizEvidence: analytics.quiz_first_attempt,
          quizRate: percent(analytics.quiz_first_attempt.rate),
          status: evidenceStatus(analytics),
        }}
      />
      <section className="course-overview-panel">
        <header>
          <div>
            <h3>{t("analytics.evidenceCoverage")}</h3>
            <p>{t("analytics.evidenceCoverageHelp")}</p>
          </div>
          <span>{t("analytics.lecturesWithEvidence", { count: coverage.available })}</span>
        </header>
        <div className="course-overview-grid">
          <section className="attention-queue">
            <h4>{t("analytics.publishedLectureEvidence")}</h4>
            <div className="attention-lecture-list">
              {rows.map(({ analytics: lectureAnalytics, lecture, snapshot }) => (
                <button key={lecture.id} type="button" onClick={() => onSelectLecture(lecture)}>
                  <span className="attention-lecture-number">{lecture.number}</span>
                  <span>
                    <strong>{lecture.title}</strong>
                    <small>
                      {t("analytics.lectureEvidenceSummary", {
                        events: snapshot.events,
                        gate: snapshot.gateRate,
                        quiz: snapshot.quizRate,
                      })}
                    </small>
                    {lectureAnalytics ? (
                      <small>
                        {t("analytics.publicationCurrent", {
                          version: lectureAnalytics.current_publication_version,
                        })}
                        {" · "}
                        {t("analytics.learningMapRevision", {
                          revision: lectureAnalytics.current_learning_map_revision,
                        })}
                      </small>
                    ) : null}
                  </span>
                  <span className={`lecture-status is-${snapshot.status}`}>
                    {statusLabel(snapshot.status, t)}
                  </span>
                </button>
              ))}
            </div>
          </section>
          <section className="signal-coverage">
            <h4>{t("analytics.evidenceCoverage")}</h4>
            <dl>
              <CoverageRow label={t("analytics.status.available")} value={coverage.available} />
              <CoverageRow
                label={t("analytics.status.insufficient")}
                value={coverage["insufficient-data"]}
              />
              <CoverageRow
                label={t("analytics.status.historical")}
                value={coverage["historical-only"]}
              />
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
    const lectureAnalytics = byId.get(lecture.id);
    return {
      analytics: lectureAnalytics,
      lecture,
      snapshot: lectureAnalytics
        ? courseLectureSnapshot(lectureAnalytics)
        : ({
            events: 0,
            gateEvidence: null,
            gateRate: "n/a",
            learners: 0,
            learningMapRevision: null,
            publicationVersion: null,
            quizEvidence: null,
            quizRate: "n/a",
            status: "no-data",
          } as const),
    };
  });
}

function evidenceStatus(analytics: CourseAnalyticsSummary): LectureSnapshot["status"] {
  if (!analytics.activity_events) return "no-data";
  if (
    analytics.quiz_first_attempt.data_status === "available" ||
    analytics.independent_first_pass.data_status === "available"
  )
    return "available";
  if (analytics.quiz_first_attempt.sample_size || analytics.independent_first_pass.sample_size)
    return "insufficient-data";
  return "historical-only";
}

function statusLabel(status: LectureSnapshot["status"], t: ReturnType<typeof useI18n>["t"]) {
  if (status === "available") return t("analytics.status.available");
  if (status === "insufficient-data") return t("analytics.status.insufficient");
  if (status === "historical-only") return t("analytics.status.historical");
  return t("analytics.status.noData");
}
