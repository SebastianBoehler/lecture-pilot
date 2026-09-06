import { useEffect, useState } from "react";
import { useI18n } from "./i18n";
import { listCourseWorkspaces } from "./professorApi";
import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { PerformanceEmptyState } from "./PerformanceBoards";
import type { LoginSession, ManagedCourseWorkspaceResult } from "./types";

export function ProfessorPerformanceDashboard({ session }: { session: LoginSession }) {
  const { t } = useI18n();
  const [courses, setCourses] = useState<ManagedCourseWorkspaceResult[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void listCourseWorkspaces(session)
      .then((items) => {
        if (active) setCourses(items.filter((item) => item.publishedLectureIds?.length));
      })
      .catch((reason: unknown) => {
        if (active)
          setError(reason instanceof Error ? reason.message : t("professor.loadCoursesFailed"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [session, reload, t]);
  const selected = courses.find((item) => item.course.id === selectedId) ?? courses[0];
  if (loading || error || !selected)
    return (
      <main className="professor-screen performance-page">
        <h1>{t("professor.performance.title")}</h1>
        {loading ? (
          <p role="status">{t("professor.loadingAnalytics")}</p>
        ) : error ? (
          <p role="alert" className="form-error">
            {error}
          </p>
        ) : (
          <PerformanceEmptyState />
        )}
        <button
          className="refresh-button"
          disabled={loading}
          onClick={() => setReload((value) => value + 1)}
        >
          {t("professor.refresh")}
        </button>
      </main>
    );
  return (
    <ProfessorCoursePerformance
      key={selected.course.id}
      session={session}
      workspaceCourse={selected.course}
      lectures={selected.lectures}
      publishedLectureIds={selected.publishedLectureIds ?? []}
      courseSelector={
        <label className="dashboard-course-select">
          {t("dashboard.course")}
          <select
            value={selected.course.id}
            onChange={(event) => setSelectedId(event.target.value)}
          >
            {courses.map((item) => (
              <option key={item.course.id} value={item.course.id}>
                {item.course.title}
              </option>
            ))}
          </select>
        </label>
      }
    />
  );
}
