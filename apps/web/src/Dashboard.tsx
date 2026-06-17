import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";
import { readDemoWorkspaceCourse } from "./demoWorkspaceAccess";

type CourseWorkspaceStatus = "matched" | "unmatched";

type CourseWorkspaceGroup = {
  course: UniversityCourse;
  status: CourseWorkspaceStatus;
  statusLabel: string;
  emptyText: string;
  tutorAvailable: boolean;
  courseLectures: Lecture[];
};

export function Dashboard({
  lectures,
  publishedLectureIds,
  session,
  workspaceCourse,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession | null;
  workspaceCourse: UniversityCourse;
  onOpen: (lecture: Lecture) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const studentLabel = session?.email ?? session?.username ?? "student";
  const courseGroups = buildCourseGroups(session, workspaceCourse, lectures, publishedLectureIds);

  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <h1>Welcome, {studentLabel}</h1>
        <p>Choose an AI tutor workspace or continue with a past lecture.</p>
      </section>

      <section className="course-panel" aria-labelledby="course-workspaces">
        <div className="panel-heading">
          <h2 id="course-workspaces">Course workspaces</h2>
        </div>
        <div className="course-workspace-list">
          {courseGroups.map(({ course, status, statusLabel, emptyText, tutorAvailable, courseLectures }) => (
            <article className={`course-workspace is-${status}`} key={`${status}-${course.id}`}>
              <div className="course-row">
                <div>
                  <h3>{course.title}</h3>
                  <p>{course.professor}</p>
                </div>
                <span className={`workspace-status is-${status}`}>{statusLabel}</span>
              </div>
              {tutorAvailable ? (
                <div className="lecture-list" aria-label={`Available lectures for ${course.title}`}>
                  {courseLectures.map((lecture) => (
                    <article className="lecture-row" key={lecture.id}>
                      <div className="lecture-number">{lecture.number}</div>
                      <div>
                        <h3>{lecture.title}</h3>
                        <p>
                          {lecture.date} · attendance {lecture.attendance}
                        </p>
                        <div className="attendance-control" aria-label={`Attendance for ${lecture.title}`}>
                          {(["present", "absent", "unknown"] as const).map((status) => (
                            <button
                              aria-pressed={lecture.attendance === status}
                              className={lecture.attendance === status ? "is-active" : undefined}
                              key={status}
                              onClick={() => onSetAttendance(lecture.id, status)}
                              type="button"
                            >
                              {status}
                            </button>
                          ))}
                        </div>
                      </div>
                      <button type="button" onClick={() => onOpen(lecture)}>
                        Open lecture {lecture.number}
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="workspace-empty">{emptyText}</p>
              )}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function buildCourseGroups(
  session: LoginSession | null,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
): CourseWorkspaceGroup[] {
  const enrolledCourses = session?.courses ?? [];
  const courseGroups = enrolledCourses.length
    ? enrolledCourses.map((course) => buildEnrolledCourseGroup(course, workspaceCourse, lectures, publishedLectureIds))
    : [buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds)];

  if (enrolledCourses.length && !enrolledCourses.some((course) => isWorkspaceCourse(course, workspaceCourse))) {
    if (hasDemoWorkspaceAccess(workspaceCourse) && publishedLectureIds.length > 0) {
      courseGroups.push(buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds));
    }
  }

  return courseGroups;
}

function buildEnrolledCourseGroup(
  course: UniversityCourse,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0 && isWorkspaceCourse(course, workspaceCourse);
  return {
    course,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? workspaceStatusLabel() : "No tutor workspace yet",
    emptyText: "No matched LecturePilot workspace for this course yet.",
    tutorAvailable,
    courseLectures: tutorAvailable ? publishedLectures : [],
  };
}

function buildDiscoverableCourseGroup(
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0;
  return {
    course: workspaceCourse,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? workspaceStatusLabel() : "No tutor workspace yet",
    emptyText: "No tutor workspace yet. Publish the course workspace to enable lecture entry.",
    tutorAvailable,
    courseLectures: publishedLectures,
  };
}

function publishedCourseLectures(lectures: Lecture[], publishedLectureIds: string[]) {
  const published = new Set(publishedLectureIds);
  return lectures.filter((lecture) => published.has(lecture.id));
}

function isWorkspaceCourse(course: UniversityCourse, workspaceCourse: UniversityCourse) {
  return course.id === workspaceCourse.id || normalizeCourseTitle(course.title) === normalizeCourseTitle(workspaceCourse.title);
}

function hasDemoWorkspaceAccess(workspaceCourse: UniversityCourse) {
  return readDemoWorkspaceCourse()?.id === workspaceCourse.id;
}

function workspaceStatusLabel() {
  return "AI tutor available";
}

function normalizeCourseTitle(title: string) {
  return title.toLowerCase().replace(/\s+/g, " ").trim();
}
