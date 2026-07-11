import { useState } from "react";

import { useI18n } from "./i18n";
import type { LearningGoal, Lecture } from "./types";

const goals: LearningGoal[] = ["keep_up", "understand_deeply", "exam_preparation"];

export function LearnerOnboarding({
  lecture,
  onComplete,
  onOpen,
}: {
  lecture: Lecture | null;
  onComplete: (goal: LearningGoal) => Promise<void>;
  onOpen: (lecture: Lecture) => void;
}) {
  const { t } = useI18n();
  const [step, setStep] = useState<1 | 2>(1);
  const [goal, setGoal] = useState<LearningGoal | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function finish() {
    if (!goal) return;
    setPending(true);
    setError(null);
    try {
      await onComplete(goal);
      if (lecture) onOpen(lecture);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : t("onboarding.failed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="onboarding-backdrop">
      <section
        aria-labelledby="onboarding-heading"
        aria-modal="true"
        className="onboarding-dialog"
        role="dialog"
      >
        <div className="onboarding-progress">
          <span>{t("onboarding.step", { current: step })}</span>
          <div aria-hidden="true">
            <i className={step === 2 ? "is-complete" : undefined} />
          </div>
        </div>

        {step === 1 ? (
          <>
            <h1 id="onboarding-heading">{t("onboarding.goal.title")}</h1>
            <p className="onboarding-copy">{t("onboarding.goal.help")}</p>
            <div className="onboarding-options">
              {goals.map((item) => (
                <button
                  aria-pressed={goal === item}
                  className={goal === item ? "is-selected" : undefined}
                  key={item}
                  type="button"
                  onClick={() => {
                    setGoal(item);
                    setStep(2);
                  }}
                >
                  <strong>{goalLabel(item, t)}</strong>
                  <span>{goalHelp(item, t)}</span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <h1 id="onboarding-heading">{t("onboarding.evidence.title")}</h1>
            <p className="onboarding-copy">{t("onboarding.evidence.help")}</p>
            <ul className="onboarding-evidence">
              <li>{t("onboarding.evidence.attempts")}</li>
              <li>{t("onboarding.evidence.adaptation")}</li>
              <li>{t("onboarding.evidence.control")}</li>
            </ul>
            {error ? <p className="form-error">{error}</p> : null}
            <div className="onboarding-actions">
              <button
                className="ghost-button"
                disabled={pending}
                type="button"
                onClick={() => setStep(1)}
              >
                {t("onboarding.back")}
              </button>
              <button
                className="onboarding-primary"
                disabled={pending}
                type="button"
                onClick={() => void finish()}
              >
                {pending
                  ? t("onboarding.saving")
                  : lecture
                    ? t("onboarding.startLecture", { number: lecture.number })
                    : t("onboarding.finish")}
              </button>
            </div>
          </>
        )}
      </section>
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
