import { useState, type FormEvent } from "react";
import { useI18n } from "../i18n/i18n";
import type { LearnerProfile } from "../shared/types";
import { LearnerPersonalizationField } from "./LearnerPersonalizationField";
import { personalizationFromPreferences } from "./learnerPersonalization";
import type { LearnerProfileState } from "./useLearnerProfile";

export function LearnerPersonalizationEditor({
  profile,
  save,
}: {
  profile: LearnerProfile;
  save: LearnerProfileState["saveCalibration"];
}) {
  const { t } = useI18n();
  const saved = personalizationFromPreferences(profile.preferences);
  const [draft, setDraft] = useState(saved);
  const [pending, setPending] = useState(false);
  const [savedOnce, setSavedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const backgroundChanged = draft.background.trim() !== saved.background;
  const examplesChanged = draft.exampleInterests.trim() !== saved.exampleInterests;
  const changed = backgroundChanged || examplesChanged;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!changed || pending) return;
    setPending(true);
    setError(null);
    setSavedOnce(false);
    try {
      await save(null, {
        background: backgroundChanged ? draft.background.trim() : undefined,
        exampleInterests: examplesChanged ? draft.exampleInterests.trim() : undefined,
        complete: true,
      });
      setSavedOnce(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("onboarding.failed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="learner-profile-section" aria-labelledby="personalization-heading">
      <div className="profile-section-intro">
        <h2 id="personalization-heading">{t("personalization.title")}</h2>
        <p>{t("personalization.disclosure")}</p>
      </div>
      <form
        className="profile-section-content learner-personalization-form"
        onSubmit={(event) => void submit(event)}
      >
        <LearnerPersonalizationField
          field="background"
          value={draft.background}
          onChange={(background) => setDraft((current) => ({ ...current, background }))}
          disabled={pending}
        />
        <LearnerPersonalizationField
          field="examples"
          value={draft.exampleInterests}
          onChange={(exampleInterests) => setDraft((current) => ({ ...current, exampleInterests }))}
          disabled={pending}
        />
        {error ? (
          <p role="alert" className="form-error">
            {error}
          </p>
        ) : null}
        {savedOnce && !changed ? <p role="status">{t("personalization.saved")}</p> : null}
        <button type="submit" className="primary-button" disabled={pending || !changed}>
          {t(pending ? "onboarding.saving" : "personalization.save")}
        </button>
      </form>
    </section>
  );
}
