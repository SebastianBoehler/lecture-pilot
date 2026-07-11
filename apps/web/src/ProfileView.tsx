import { useEffect, useState } from "react";

import {
  listProfessorRequests,
  requestProfessorAccess,
  reviewProfessorRequest,
  type ProfessorRequest,
} from "./accountApi";
import { useI18n } from "./i18n";
import { LearnerProfileControls } from "./LearnerProfileControls";
import type { LoginSession } from "./types";
import type { LearnerProfileState } from "./useLearnerProfile";

export function ProfileView({
  session,
  onBack,
  onSessionChange,
  learnerProfileState,
}: {
  session: LoginSession;
  onBack?: () => void;
  onSessionChange: (session: LoginSession) => void;
  learnerProfileState?: LearnerProfileState;
}) {
  const { t } = useI18n();
  const [requests, setRequests] = useState<ProfessorRequest[]>([]);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const isPlatformAdmin = session.roles?.includes("tenant_admin") ?? false;

  useEffect(() => {
    if (!isPlatformAdmin) return;
    void listProfessorRequests(session)
      .then(setRequests)
      .catch((error) =>
        setAccountError(error instanceof Error ? error.message : "Request loading failed."),
      );
  }, [isPlatformAdmin, session]);

  async function requestProfessor() {
    setPending(true);
    setAccountError(null);
    try {
      const request = await requestProfessorAccess(session);
      onSessionChange({ ...session, professor_status: request.status });
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "Professor request failed.");
    } finally {
      setPending(false);
    }
  }

  async function review(requestId: string, decision: "approve" | "reject") {
    setPending(true);
    setAccountError(null);
    try {
      await reviewProfessorRequest(requestId, decision, session);
      setRequests(await listProfessorRequests(session));
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : "Professor request review failed.");
    } finally {
      setPending(false);
    }
  }
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
            <dt>{t("profile.username")}</dt>
            <dd>{session.username}</dd>
          </div>
          <div>
            <dt>{t("profile.email")}</dt>
            <dd>{session.email || t("profile.notLoaded")}</dd>
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
            <dd>{session.courses.length}</dd>
          </div>
        </dl>

        {session.auth_transport === "cookie" && session.account_type === "professor" ? (
          <section className="profile-settings" aria-labelledby="professor-access-heading">
            <h2 id="professor-access-heading">Professor access</h2>
            <p>Status: {session.professor_status ?? "not_requested"}</p>
            {session.professor_status === "not_requested" ||
            session.professor_status === "rejected" ? (
              <button disabled={pending} type="button" onClick={() => void requestProfessor()}>
                Request professor approval
              </button>
            ) : null}
          </section>
        ) : null}

        {isPlatformAdmin ? (
          <section className="profile-settings" aria-labelledby="platform-requests-heading">
            <h2 id="platform-requests-heading">Pending professor requests</h2>
            {requests.length ? (
              requests.map((request) => (
                <article className="course-row" key={request.id}>
                  <div>
                    <strong>{request.username}</strong>
                    <small>{request.email ?? "No email returned"}</small>
                    {request.university_role ? (
                      <small>Alma role: {request.university_role}</small>
                    ) : null}
                  </div>
                  <div>
                    <button
                      disabled={pending}
                      type="button"
                      onClick={() => void review(request.id, "approve")}
                    >
                      Approve
                    </button>
                    <button
                      disabled={pending}
                      type="button"
                      onClick={() => void review(request.id, "reject")}
                    >
                      Reject
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p>No pending requests.</p>
            )}
          </section>
        ) : null}
        {accountError ? <p className="form-error">{accountError}</p> : null}

        {learnerProfileState ? (
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
          </div>
        </section>
      </section>
    </main>
  );
}
