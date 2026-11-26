import { useI18n } from "../i18n/i18n";
import { PERSONALIZATION_LENGTH } from "./learnerPersonalization";
import "./learner-personalization.css";

export function LearnerPersonalizationField({
  field,
  value,
  onChange,
  disabled,
}: {
  field: "background" | "examples";
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  const { t } = useI18n();
  return (
    <label className="learner-personalization-field">
      {t(`personalization.${field}.label`)}
      <textarea
        rows={3}
        maxLength={PERSONALIZATION_LENGTH}
        placeholder={t(`personalization.${field}.placeholder`)}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
      />
    </label>
  );
}
