import { useState } from "react";

import { useI18n } from "./i18n";
import { LearnerCourseFiles } from "./LearnerCourseFiles";
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
  if (state.loading && !profile)
    return <p className="profile-status">{t("profile.learning.loading")}</p>;
  if (!profile) return state.error ? <p className="form-error">{state.error}</p> : null;

  const visiblePreferences = Object.entries(profile.preferences).filter(
    ([key]) => !systemPreferences.has(key),
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
        <h2 id="learning-goal-heading">{t("profile.goal.title")}</h2>
        <p>{t("profile.goal.help")}</p>
        <div className="profile-goal-options">
          {goals.map((goal) => (
            <button
              aria-pressed={profile.learning_goal === goal}
              disabled={pending}
              key={goal}
              type="button"
              onClick={() => void run(() => state.saveCalibration(goal))}
            >
              {goalLabel(goal, t)}
            </button>
          ))}
        </div>
      </section>

      <section className="learner-profile-section" aria-labelledby="stored-memory-heading">
        <h2 id="stored-memory-heading">{t("profile.memory.title")}</h2>
        <p>{t("profile.memory.help")}</p>
        <div className="stored-memory-block">
          <div>
            <strong>{t("profile.memory.global")}</strong>
            <p>{profile.global_notes || t("profile.memory.empty")}</p>
          </div>
          {profile.global_notes ? (
            <button
              disabled={pending}
              type="button"
              onClick={() => void run(() => state.clearMemory())}
            >
              {t("profile.memory.clearGlobal")}
            </button>
          ) : null}
        </div>
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
        ) : (
          <p className="profile-empty-copy">{t("profile.preference.empty")}</p>
        )}
      </section>

      <LearnerCourseFiles
        courses={session.courses}
        profiles={profile.courses}
        pending={pending}
        onClearMemory={(courseId) => run(() => state.clearMemory(courseId))}
      />
      {state.error ? <p className="form-error">{state.error}</p> : null}
    </div>
  );
}

function goalLabel(goal: LearningGoal, t: ReturnType<typeof useI18n>["t"]) {
  if (goal === "keep_up") return t("learningGoal.keepUp");
  if (goal === "exam_preparation") return t("learningGoal.examPreparation");
  return t("learningGoal.understandDeeply");
}

function formatValue(value: unknown) {
  return typeof value === "string" ? value : JSON.stringify(value);
}
