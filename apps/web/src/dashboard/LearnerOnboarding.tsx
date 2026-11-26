import { useLayoutEffect, useRef, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { LearnerPersonalizationField } from "../profile/LearnerPersonalizationField";
import {
  personalizationFromPreferences,
  type LearnerPersonalizationUpdate,
} from "../profile/learnerPersonalization";
import type { LearnerProfile, LearningGoal } from "../shared/types";
import { useModalDialog } from "../shared/useModalDialog";

const goals = [
  ["keep_up", "keepUp"],
  ["understand_deeply", "understandDeeply"],
  ["exam_preparation", "examPreparation"],
] as const;
const steps = ["goal", "background", "examples"] as const;

export function LearnerOnboarding({
  profile,
  onComplete,
}: {
  profile?: LearnerProfile;
  onComplete: (
    goal: LearningGoal | null,
    personalization: LearnerPersonalizationUpdate,
  ) => Promise<void>;
}) {
  const { t } = useI18n();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState<LearningGoal | null>(profile?.learning_goal ?? null);
  const [details, setDetails] = useState(() =>
    personalizationFromPreferences(profile?.preferences),
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saving = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const dialogRef = useModalDialog();
  const last = step === steps.length - 1;

  useLayoutEffect(() => {
    heading.current?.focus();
  }, [step]);

  async function finish(skip: boolean) {
    if (saving.current) return;
    saving.current = true;
    setPending(true);
    setError(null);
    try {
      await onComplete(
        skip ? null : goal,
        skip ? { complete: true } : { ...details, complete: true },
      );
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : t("onboarding.failed"));
    } finally {
      saving.current = false;
      setPending(false);
    }
  }

  return (
    <dialog
      aria-labelledby="onboarding-heading"
      aria-modal="true"
      className="onboarding-dialog"
      ref={dialogRef}
      onCancel={(event) => {
        event.preventDefault();
        void finish(true);
      }}
    >
      <div className="onboarding-progress">
        <span>{t("onboarding.step", { current: step + 1 })}</span>
        <div aria-hidden="true">
          <i style={{ width: `${(100 * (step + 1)) / steps.length}%` }} />
        </div>
      </div>
      <h1 id="onboarding-heading" ref={heading} tabIndex={-1}>
        {t(`onboarding.${steps[step]}.title`)}
      </h1>
      <p className="onboarding-copy">{t(`onboarding.${steps[step]}.help`)}</p>
      {step === 0 ? (
        <div className="onboarding-options">
          {goals.map(([value, label]) => (
            <button
              aria-pressed={goal === value}
              className={goal === value ? "is-selected" : undefined}
              disabled={pending}
              key={value}
              type="button"
              onClick={() => {
                setGoal(value);
                setStep(1);
              }}
            >
              <strong>{t(`learningGoal.${label}`)}</strong>
              <span>{t(`learningGoal.${label}.help`)}</span>
            </button>
          ))}
        </div>
      ) : step === 1 ? (
        <LearnerPersonalizationField
          field="background"
          value={details.background}
          onChange={(background) => setDetails((current) => ({ ...current, background }))}
          disabled={pending}
        />
      ) : (
        <LearnerPersonalizationField
          field="examples"
          value={details.exampleInterests}
          onChange={(exampleInterests) =>
            setDetails((current) => ({ ...current, exampleInterests }))
          }
          disabled={pending}
        />
      )}
      {last ? <p className="onboarding-disclosure">{t("personalization.disclosure")}</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="onboarding-actions">
        <button
          className="ghost-button"
          disabled={pending}
          type="button"
          onClick={() => void finish(true)}
        >
          {t("onboarding.skip")}
        </button>
        <div>
          {step > 0 ? (
            <button
              className="ghost-button"
              disabled={pending}
              type="button"
              onClick={() => setStep((current) => current - 1)}
            >
              {t("onboarding.back")}
            </button>
          ) : null}
          {step > 0 || goal ? (
            <button
              className="onboarding-primary"
              disabled={pending}
              type="button"
              onClick={() => (last ? void finish(false) : setStep((current) => current + 1))}
            >
              {t(
                pending
                  ? "onboarding.saving"
                  : last
                    ? "onboarding.goToDashboard"
                    : "onboarding.continue",
              )}
            </button>
          ) : null}
        </div>
      </div>
    </dialog>
  );
}
