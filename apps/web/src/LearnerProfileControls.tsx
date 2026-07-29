import { useState } from "react";
import { BrainCircuit, CalendarClock, Check, GraduationCap, Network } from "lucide-react";

import { useI18n } from "./i18n";
import { LearnerCourseFiles } from "./LearnerCourseFiles";
import { findProfileCourse, humanizeCourseId } from "./profileCourseDisplay";
import type { LearningGoal, LoginSession } from "./types";
import type { LearnerProfileState } from "./useLearnerProfile";

const goals: LearningGoal[] = ["keep_up", "understand_deeply", "exam_preparation"];
const systemPreferences = new Set(["learning_goal", "onboarding_completed"]);

export function LearnerProfileControls({
  session,
  state,
}: {
  session: LoginSession;
  state: LearnerProfileState;
}) {
  const { t } = useI18n();
  const [pending, setPending] = useState(false);
  const profile = state.profile;
  if (state.loading && !profile) {
    return (
      <section className="learner-profile-section" aria-labelledby="learning-profile-heading">
        <div className="profile-section-intro">
          <h2 id="learning-profile-heading">{t("profile.learning.title")}</h2>
          <p>{t("profile.learning.help")}</p>
        </div>
        <p className="profile-status" role="status">
          {t("profile.learning.loading")}
        </p>
      </section>
    );
  }
  if (!profile) return state.error ? <p className="form-error">{state.error}</p> : null;

  const visiblePreferences = Object.entries(profile.preferences).filter(
    ([key]) => !systemPreferences.has(key),
  );
  const courseMemories = profile.courses.filter((course) => course.memory);
  const hasPersonalization = Boolean(
    profile.global_notes || visiblePreferences.length || courseMemories.length,
  );
  async function run(action: () => Promise<void>) {
    setPending(true);
    try {
      await action();
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="learner-profile-controls">
      <section className="learner-profile-section" aria-labelledby="learning-goal-heading">
        <div className="profile-section-intro">
          <h2 id="learning-goal-heading">{t("profile.goal.title")}</h2>
          <p>{t("profile.goal.help")}</p>
        </div>
        <div className="profile-section-content">
          <div className="profile-goal-options">
            {goals.map((goal) => (
              <button
                aria-pressed={profile.learning_goal === goal}
                disabled={pending}
                key={goal}
                type="button"
                onClick={() => void run(() => state.saveCalibration(goal))}
              >
                <span className="profile-goal-icon" aria-hidden="true">
                  {goalIcon(goal)}
                </span>
                <span className="profile-goal-copy">
                  <strong>{goalLabel(goal, t)}</strong>
                  <small>{goalHelp(goal, t)}</small>
                </span>
                {profile.learning_goal === goal ? (
                  <Check className="profile-goal-check" aria-hidden="true" size={18} />
                ) : null}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="learner-profile-section" aria-labelledby="stored-memory-heading">
        <div className="profile-section-intro">
          <h2 id="stored-memory-heading">{t("profile.memory.title")}</h2>
          <p>{t("profile.memory.help")}</p>
        </div>
        <div className="profile-section-content">
          {hasPersonalization ? (
            <>
              {profile.global_notes ? (
                <div className="stored-memory-block">
                  <div>
                    <strong>{t("profile.memory.global")}</strong>
                    <p>{profile.global_notes}</p>
                  </div>
                  <button
                    disabled={pending}
                    type="button"
                    onClick={() => void run(() => state.clearMemory())}
                  >
                    {t("profile.memory.clearGlobal")}
                  </button>
                </div>
              ) : null}
              {courseMemories.map((course) => (
                <div className="stored-memory-block" key={course.course_id}>
                  <div>
                    <strong>{courseTitle(course.course_id, session)}</strong>
                    <p>{course.memory}</p>
                  </div>
                  <button
                    disabled={pending}
                    type="button"
                    onClick={() => void run(() => state.clearMemory(course.course_id))}
                  >
                    {t("profile.memory.clearCourse")}
                  </button>
                </div>
              ))}
              {visiblePreferences.length ? (
                <div className="preference-list">
                  {visiblePreferences.map(([key, value]) => (
                    <div key={key}>
                      <span>
                        <strong>{key}</strong>
                        <small>{formatValue(value)}</small>
                      </span>
                      <button
                        aria-label={t("profile.preference.remove", { key })}
                        disabled={pending}
                        type="button"
                        onClick={() => void run(() => state.removePreference(key))}
                      >
                        {t("profile.preference.removeShort")}
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}
            </>
          ) : (
            <div className="profile-empty-state">
              <BrainCircuit aria-hidden="true" size={20} />
              <div>
                <strong>{t("profile.memory.empty")}</strong>
                <p>{t("profile.memory.emptyHelp")}</p>
              </div>
            </div>
          )}
        </div>
      </section>

      <LearnerCourseFiles courses={session.courses} profiles={profile.courses} />
      {state.error ? <p className="form-error">{state.error}</p> : null}
    </div>
  );
}

function goalLabel(goal: LearningGoal, t: ReturnType<typeof useI18n>["t"]) {
  if (goal === "keep_up") return t("learningGoal.keepUp");
  if (goal === "exam_preparation") return t("learningGoal.examPreparation");
  return t("learningGoal.understandDeeply");
}

function goalHelp(goal: LearningGoal, t: ReturnType<typeof useI18n>["t"]) {
  if (goal === "keep_up") return t("learningGoal.keepUp.help");
  if (goal === "exam_preparation") return t("learningGoal.examPreparation.help");
  return t("learningGoal.understandDeeply.help");
}

function goalIcon(goal: LearningGoal) {
  if (goal === "keep_up") return <CalendarClock size={19} />;
  if (goal === "exam_preparation") return <GraduationCap size={19} />;
  return <Network size={19} />;
}

function formatValue(value: unknown) {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function courseTitle(courseId: string, session: LoginSession) {
  return findProfileCourse(courseId, session.courses)?.title || humanizeCourseId(courseId);
}
