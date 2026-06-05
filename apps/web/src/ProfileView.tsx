import type { LoginSession } from "./types";

export function ProfileView({
  session,
  onBack,
}: {
  session: LoginSession;
  onBack: () => void;
}) {
  return (
    <main className="profile-screen">
      <section className="profile-panel" aria-labelledby="profile-heading">
        <div className="panel-heading">
          <div>
            <p className="section-label">Account</p>
            <h1 id="profile-heading">Profile</h1>
          </div>
          <button className="ghost-button" type="button" onClick={onBack}>
            Dashboard
          </button>
        </div>

        <dl className="profile-fields">
          <div>
            <dt>Username</dt>
            <dd>{session.username}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{session.email || "Not loaded"}</dd>
          </div>
          <div>
            <dt>Term</dt>
            <dd>{session.term}</dd>
          </div>
          <div>
            <dt>Courses</dt>
            <dd>{session.courses.length}</dd>
          </div>
        </dl>

        <section className="profile-courses" aria-labelledby="profile-courses-heading">
          <h2 id="profile-courses-heading">Loaded Courses</h2>
          <div className="course-list">
            {session.courses.map((course) => (
              <article className="course-row" key={course.id}>
                <div>
                  <h3>{course.title}</h3>
                  <p>{course.professor}</p>
                </div>
                <span>{course.term}</span>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
