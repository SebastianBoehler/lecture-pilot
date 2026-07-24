import { LogOut } from "lucide-react";

import { useI18n } from "./i18n";
import { LearnerProfileControls } from "./LearnerProfileControls";
import type { LoginSession } from "./types";
import type { LearnerProfileState } from "./useLearnerProfile";

export function ProfileView({
  session,
  onLogout,
  learnerProfileState,
}: {
  session: LoginSession;
  onLogout: () => void;
  learnerProfileState?: LearnerProfileState;
}) {
  const { t } = useI18n();
  const syncLoading = session.university_course_sync_status === "loading";
  const hasLearnerWorkspace = session.roles?.includes("student") === true;
  const displayName =
    session.display_name || t(syncLoading ? "profile.loading" : "profile.notLoaded");
  const email = session.email || t(syncLoading ? "profile.loading" : "profile.notLoaded");
  return (
    <main className="profile-screen">
      <section className="profile-panel" aria-labelledby="profile-heading">
        <header className="profile-view-header">
          <div>
            <h1 id="profile-heading">{t("profile.title")}</h1>
          </div>
          <div className="profile-view-actions">
            <button className="profile-logout-button" type="button" onClick={onLogout}>
              <LogOut aria-hidden="true" size={16} />
              <span>{t("nav.logout")}</span>
            </button>
          </div>
        </header>

        <section className="profile-account-summary" aria-label={t("profile.account")}>
          <div className="profile-identity">
            <span className="profile-avatar" aria-hidden="true">
              {profileInitials(session.display_name, session.username)}
            </span>
            <div className="profile-identity-copy">
              <h2>{displayName}</h2>
              <p>{email}</p>
              <span>{session.username}</span>
            </div>
          </div>
          <dl className="profile-facts">
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
        </section>

        {hasLearnerWorkspace && learnerProfileState ? (
          <LearnerProfileControls session={session} state={learnerProfileState} />
        ) : null}

        <section className="profile-courses" aria-labelledby="profile-courses-heading">
          <div className="profile-section-intro">
            <h2 id="profile-courses-heading">{t("profile.loadedCourses")}</h2>
          </div>
          <div className="profile-section-content">
            <div className="course-list profile-course-list">
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
              {syncLoading ? (
                <p className="workspace-empty">{t("profile.loadingCourses")}</p>
              ) : null}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

function profileInitials(displayName: string | null | undefined, username: string) {
  const name = displayName?.trim() || username;
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}
