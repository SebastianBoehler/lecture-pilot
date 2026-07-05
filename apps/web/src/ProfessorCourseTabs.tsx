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
  return (
    <nav className="performance-course-tabs" aria-label="Performance course scope">
      <div>
        <span>Course scope</span>
        <small>Switch between professor courses and published tutor workspaces.</small>
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
              <small>{workspaceActive ? `${publishedLectureCount} published lectures` : "No workspace yet"}</small>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export function performanceCourseOptions(courses: UniversityCourse[], workspaceCourse: UniversityCourse) {
  const options = new Map<string, UniversityCourse>();
  options.set(workspaceCourse.id, workspaceCourse);
  for (const course of courses) {
    if (!options.has(course.id)) options.set(course.id, course);
  }
  return Array.from(options.values());
}
