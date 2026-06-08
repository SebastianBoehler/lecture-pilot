import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";

const demoTutorCourse: UniversityCourse = {
  id: "martius-ml",
  title: "Grundlagen des Maschinellen Lernens",
  professor: "Prof. Georg Martius",
  term: "Sommer 2026",
};

export function Dashboard({
  lectures,
  tutorWorkspacePublished,
  session,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  tutorWorkspacePublished: boolean;
  session: LoginSession | null;
  onOpen: (lecture: Lecture) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const studentLabel = session?.email ?? session?.username ?? "student";
  const courseGroups = buildCourseGroups(session, lectures, tutorWorkspacePublished);

  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <p className="section-label">Student workspace</p>
        <h1>Welcome, {studentLabel}</h1>
        <p>Choose an AI tutor workspace or continue with a past lecture.</p>
      </section>

      <section className="course-panel" aria-labelledby="course-workspaces">
        <div className="panel-heading">
          <h2 id="course-workspaces">Course workspaces</h2>
          <span>{session ? `Connected as ${session.username}` : "Only past dates are shown"}</span>
        </div>
        <div className="course-workspace-list">
          {courseGroups.map(({ course, tutorAvailable, courseLectures }) => (
            <article className="course-workspace" key={course.id}>
              <div className="course-row">
                <div>
                  <h3>{course.title}</h3>
                  <p>{course.professor}</p>
                </div>
                <span>{tutorAvailable ? "AI tutor available" : "No tutor workspace yet"}</span>
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
                <p className="workspace-empty">No matched LecturePilot workspace for this course yet.</p>
              )}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function buildCourseGroups(session: LoginSession | null, lectures: Lecture[], tutorWorkspacePublished: boolean) {
  const courses = session?.courses.length ? withDemoTutorCourse(session.courses) : [demoTutorCourse];
  return courses.map((course) => {
    const tutorAvailable = tutorWorkspacePublished && isDemoTutorCourse(course);
    return { course, tutorAvailable, courseLectures: tutorAvailable ? lectures : [] };
  });
}

function withDemoTutorCourse(courses: UniversityCourse[]) {
  if (courses.some(isDemoTutorCourse)) {
    return courses;
  }
  return [...courses, demoTutorCourse];
}

function isDemoTutorCourse(course: UniversityCourse) {
  return course.id === demoTutorCourse.id || normalizeCourseTitle(course.title) === normalizeCourseTitle(demoTutorCourse.title);
}

function normalizeCourseTitle(title: string) {
  return title.toLowerCase().replace(/\s+/g, " ").trim();
}
