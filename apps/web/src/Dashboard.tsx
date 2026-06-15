import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";

type CourseWorkspaceStatus = "matched" | "demo" | "unmatched";

type CourseWorkspaceGroup = {
  course: UniversityCourse;
  status: CourseWorkspaceStatus;
  statusLabel: string;
  helperText: string | null;
  emptyText: string;
  tutorAvailable: boolean;
  courseLectures: Lecture[];
};

const demoTutorCourse: UniversityCourse = {
  access_policy: "public",
  id: "martius-ml",
  title: "Grundlagen des Maschinellen Lernens",
  professor: "Prof. Georg Martius",
  term: "Sommer 2026",
};

export function Dashboard({
  lectures,
  publishedLectureIds,
  session,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession | null;
  onOpen: (lecture: Lecture) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const studentLabel = session?.email ?? session?.username ?? "student";
  const courseGroups = buildCourseGroups(session, lectures, publishedLectureIds);

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
          {courseGroups.map(({ course, status, statusLabel, helperText, emptyText, tutorAvailable, courseLectures }) => (
            <article className={`course-workspace is-${status}`} key={`${status}-${course.id}`}>
              <div className="course-row">
                <div>
                  <h3>{course.title}</h3>
                  <p>{course.professor}</p>
                </div>
                <span className={`workspace-status is-${status}`}>{statusLabel}</span>
              </div>
              {helperText ? <p className="workspace-helper">{helperText}</p> : null}
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
  lectures: Lecture[],
  publishedLectureIds: string[],
): CourseWorkspaceGroup[] {
  const enrolledCourses = session?.courses ?? [];
  const courseGroups = enrolledCourses.length
    ? enrolledCourses.map((course) => buildEnrolledCourseGroup(course, lectures, publishedLectureIds))
    : [buildDemoCourseGroup(lectures, publishedLectureIds)];

  if (enrolledCourses.length && !enrolledCourses.some(isDemoTutorCourse)) {
    if (isDiscoverableTutorCourse(demoTutorCourse)) {
      courseGroups.push(buildDemoCourseGroup(lectures, publishedLectureIds));
    }
  }

  return courseGroups;
}

function buildEnrolledCourseGroup(
  course: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0 && isDemoTutorCourse(course);
  return {
    course,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? workspaceStatusLabel(course) : "No tutor workspace yet",
    helperText: null,
    emptyText: "No matched LecturePilot workspace for this course yet.",
    tutorAvailable,
    courseLectures: tutorAvailable ? publishedLectures : [],
  };
}

function buildDemoCourseGroup(lectures: Lecture[], publishedLectureIds: string[]): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  return {
    course: demoTutorCourse,
    status: "demo",
    statusLabel: workspaceStatusLabel(demoTutorCourse),
    helperText: "Open course workspace; not part of your current Alma enrollment.",
    emptyText: "No tutor workspace yet. Publish the demo workspace to enable lecture entry.",
    tutorAvailable: publishedLectures.length > 0,
    courseLectures: publishedLectures,
  };
}

function publishedCourseLectures(lectures: Lecture[], publishedLectureIds: string[]) {
  const published = new Set(publishedLectureIds);
  return lectures.filter((lecture) => published.has(lecture.id));
}

function isDemoTutorCourse(course: UniversityCourse) {
  return course.id === demoTutorCourse.id || normalizeCourseTitle(course.title) === normalizeCourseTitle(demoTutorCourse.title);
}

function isDiscoverableTutorCourse(course: UniversityCourse) {
  return course.access_policy === "public" || course.access_policy === "platform_authenticated";
}

function workspaceStatusLabel(course: UniversityCourse) {
  if (course.access_policy === "public") return "Public workspace";
  return "AI tutor available";
}

function normalizeCourseTitle(title: string) {
  return title.toLowerCase().replace(/\s+/g, " ").trim();
}
