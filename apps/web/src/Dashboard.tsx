import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";

export function Dashboard({
  lectures,
  session,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  session: LoginSession | null;
  onOpen: (lecture: Lecture) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <p className="section-label">Sommer 2026</p>
        <h1>Grundlagen des Maschinellen Lernens</h1>
        <p>Prof. Georg Martius</p>
      </section>

      {session ? (
        <section className="course-panel account-panel" aria-labelledby="connected-courses">
          <div className="panel-heading">
            <h2 id="connected-courses">Connected as {session.username}</h2>
            <span>{session.term}</span>
          </div>
          <div className="course-list">
            {session.courses.map((course) => (
              <article className="course-row" key={course.id}>
                <div>
                  <h3>{course.title}</h3>
                  <p>{course.professor}</p>
                </div>
                <span>{hasTutorWorkspace(course) ? "AI tutor available" : course.term}</span>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="course-panel" aria-labelledby="available-lectures">
        <div className="panel-heading">
          <h2 id="available-lectures">Available lectures</h2>
          <span>Only past dates are shown</span>
        </div>
        <div className="lecture-list">
          {lectures.map((lecture) => (
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
      </section>
    </main>
  );
}

function hasTutorWorkspace(course: UniversityCourse) {
  const normalized = `${course.id} ${course.title}`.toLowerCase();
  return normalized.includes("machine learning") || normalized.includes("maschinellen lernens");
}
