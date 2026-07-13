import { useI18n } from "./i18n";
import { LearnerProfileControls } from "./LearnerProfileControls";
import type { LoginSession } from "./types";
import type { LearnerProfileState } from "./useLearnerProfile";

export function ProfileView({
  session,
  onBack,
  learnerProfileState,
}: {
  session: LoginSession;
  onBack?: () => void;
  learnerProfileState?: LearnerProfileState;
}) {
  const { t } = useI18n();
  const syncLoading = session.university_course_sync_status === "loading";
  const hasLearnerWorkspace = session.roles?.includes("student") === true;
  return (
    <main className="profile-screen">
      <section className="profile-panel" aria-labelledby="profile-heading">
        <div className="panel-heading">
          <div>
            <p className="section-label">{t("profile.account")}</p>
            <h1 id="profile-heading">{t("profile.title")}</h1>
          </div>
          {onBack ? (
            <button className="ghost-button" type="button" onClick={onBack}>
              {t("lesson.back.dashboard")}
            </button>
          ) : null}
        </div>

        <dl className="profile-fields">
          <div>
            <dt>{t("profile.name")}</dt>
            <dd>
              {session.display_name || t(syncLoading ? "profile.loading" : "profile.notLoaded")}
            </dd>
          </div>
          <div>
            <dt>{t("profile.username")}</dt>
            <dd>{session.username}</dd>
          </div>
          <div>
            <dt>{t("profile.email")}</dt>
            <dd>{session.email || t(syncLoading ? "profile.loading" : "profile.notLoaded")}</dd>
          </div>
          {session.university_role ? (
            <div>
              <dt>{t("profile.universityRole")}</dt>
              <dd>{session.university_role}</dd>
            </div>
          ) : null}
          <div>
            <dt>{t("profile.term")}</dt>
            <dd>{session.term}</dd>
          </div>
          <div>
            <dt>{t("profile.courses")}</dt>
            <dd>{syncLoading ? t("profile.loading") : session.courses.length}</dd>
          </div>
        </dl>

        {hasLearnerWorkspace && learnerProfileState ? (
          <LearnerProfileControls session={session} state={learnerProfileState} />
        ) : null}

        <section className="profile-courses" aria-labelledby="profile-courses-heading">
          <h2 id="profile-courses-heading">{t("profile.loadedCourses")}</h2>
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
            {!syncLoading && session.courses.length === 0 ? (
              <p className="workspace-empty">{t("profile.noWorkspaces")}</p>
            ) : null}
            {syncLoading ? <p className="workspace-empty">{t("profile.loadingCourses")}</p> : null}
          </div>
        </section>
      </section>
    </main>
  );
}
