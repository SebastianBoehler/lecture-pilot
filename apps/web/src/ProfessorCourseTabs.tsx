import { useI18n } from "./i18n";
import type { UniversityCourse } from "./types";

export function ProfessorCourseTabs({
  courses,
  publishedLectureCount,
  selectedCourseId,
  workspaceCourseId,
  onSelect,
}: {
  courses: UniversityCourse[];
  publishedLectureCount: number;
  selectedCourseId: string;
  workspaceCourseId: string;
  onSelect: (courseId: string) => void;
}) {
  const { t } = useI18n();
  return (
    <nav className="performance-course-tabs" aria-label={t("professor.tabs.scopeAria")}>
      <div>
        <span>{t("professor.tabs.scope")}</span>
        <small>{t("professor.tabs.scopeHelp")}</small>
      </div>
      <div className="performance-course-tab-list">
        {courses.map((course) => {
          const workspaceActive = course.id === workspaceCourseId;
          return (
            <button
              aria-pressed={selectedCourseId === course.id}
              className={selectedCourseId === course.id ? "is-active" : undefined}
              key={course.id}
              type="button"
              onClick={() => onSelect(course.id)}
            >
              <strong>{course.title}</strong>
              <small>
                {workspaceActive
                  ? t("professor.publishedLectures", { count: publishedLectureCount })
                  : t("professor.tabs.noWorkspace")}
              </small>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export function performanceCourseOptions(
  courses: UniversityCourse[],
  workspaceCourse: UniversityCourse,
  includeWorkspaceCourse = true,
) {
  const options = new Map<string, UniversityCourse>();
  if (includeWorkspaceCourse) options.set(workspaceCourse.id, workspaceCourse);
  for (const course of courses) {
    if (!options.has(course.id)) options.set(course.id, course);
  }
  return Array.from(options.values());
}
