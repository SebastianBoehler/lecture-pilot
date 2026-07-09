import { useI18n } from "./i18n";
import type { LoginSession } from "./types";
import { TUTOR_MODEL_OPTIONS, type TutorModelPreference } from "./tutorModels";

export function ProfileView({
  modelPreference,
  session,
  onBack,
  onModelPreferenceChange,
}: {
  modelPreference: TutorModelPreference;
  session: LoginSession;
  onBack: () => void;
  onModelPreferenceChange: (preference: TutorModelPreference) => void;
}) {
  const { t } = useI18n();
  return (
    <main className="profile-screen">
      <section className="profile-panel" aria-labelledby="profile-heading">
        <div className="panel-heading">
          <div>
            <p className="section-label">{t("profile.account")}</p>
            <h1 id="profile-heading">{t("profile.title")}</h1>
          </div>
          <button className="ghost-button" type="button" onClick={onBack}>
            {t("lesson.back.dashboard")}
          </button>
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
          <div>
            <dt>{t("profile.term")}</dt>
            <dd>{session.term}</dd>
          </div>
          <div>
            <dt>{t("profile.courses")}</dt>
            <dd>{session.courses.length}</dd>
          </div>
        </dl>

        <section className="profile-settings" aria-labelledby="profile-settings-heading">
          <h2 id="profile-settings-heading">{t("profile.settings")}</h2>
          <label className="profile-setting-row">
            <span>
              <strong>{t("profile.tutorModel")}</strong>
              <small>{t("profile.tutorModelHelp")}</small>
            </span>
            <select
              aria-label={t("profile.tutorModelPreference")}
              value={modelPreference}
              onChange={(event) =>
                onModelPreferenceChange(event.target.value as TutorModelPreference)
              }
            >
              {TUTOR_MODEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <p>{TUTOR_MODEL_OPTIONS.find((option) => option.value === modelPreference)?.detail}</p>
        </section>

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
