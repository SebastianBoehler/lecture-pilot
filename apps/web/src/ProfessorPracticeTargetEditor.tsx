import { useI18n } from "./i18n";
import type { PracticeTarget } from "./practiceDesignTypes";

export function ProfessorPracticeTargetEditor({
  disabled,
  target,
  onChange,
}: {
  disabled: boolean;
  target: PracticeTarget;
  onChange: (target: PracticeTarget) => void;
}) {
  const { t } = useI18n();
  return (
    <details className="practice-target-editor">
      <summary>{t("builder.design.editTarget")}</summary>
      <div className="practice-target-fields">
        <TextField
          label={t("builder.design.targetTitle")}
          disabled={disabled}
          value={target.title}
          onChange={(title) => onChange({ ...target, title })}
        />
        <TextField
          label={t("builder.design.outcomeFor", { target: target.title })}
          disabled={disabled}
          value={target.outcome}
          onChange={(outcome) => onChange({ ...target, outcome })}
        />
        <TextField
          label={t("builder.design.baseline")}
          disabled={disabled}
          value={target.baseline_task}
          onChange={(baseline_task) => onChange({ ...target, baseline_task })}
        />
        <TextField
          label={t("builder.design.exit")}
          disabled={disabled}
          value={target.independent_exit_task}
          onChange={(independent_exit_task) => onChange({ ...target, independent_exit_task })}
        />
        <TextField
          label={t("builder.design.transfer")}
          disabled={disabled}
          value={target.delayed_transfer_task}
          onChange={(delayed_transfer_task) => onChange({ ...target, delayed_transfer_task })}
        />
        <label>
          {t("builder.design.reviewAfterDays")}
          <input
            min="1"
            max="365"
            type="number"
            disabled={disabled}
            value={target.review_after_days}
            onChange={(event) =>
              onChange({ ...target, review_after_days: Number(event.target.value) })
            }
          />
        </label>
        <TextField
          label={t("builder.design.sources")}
          disabled={disabled}
          value={target.source_refs.join("\n")}
          onChange={(sourceRefs) =>
            onChange({ ...target, source_refs: sourceRefs.split("\n").filter(Boolean) })
          }
        />
      </div>
      <TargetList
        label={t("builder.design.evidence")}
        disabled={disabled}
        items={target.evidence_criteria.map((item) => item.description)}
        onChange={(values) =>
          onChange({
            ...target,
            evidence_criteria: target.evidence_criteria.map((item, index) => ({
              ...item,
              description: values[index] ?? "",
            })),
          })
        }
      />
      <TargetList
        label={t("builder.design.misconceptions")}
        disabled={disabled}
        items={target.misconceptions.map((item) => `${item.description}\n${item.diagnostic_cue}`)}
        onChange={(values) =>
          onChange({
            ...target,
            misconceptions: target.misconceptions.map((item, index) => {
              const [description = "", diagnostic_cue = ""] = (values[index] ?? "").split("\n");
              return { ...item, description, diagnostic_cue };
            }),
          })
        }
      />
      <TargetList
        label={t("builder.design.hints")}
        disabled={disabled}
        items={target.hint_ladder.map((item) => item.content)}
        onChange={(values) =>
          onChange({
            ...target,
            hint_ladder: target.hint_ladder.map((item, index) => ({
              ...item,
              content: values[index] ?? "",
            })),
          })
        }
      />
    </details>
  );
}

function TextField({
  disabled,
  label,
  value,
  onChange,
}: {
  disabled: boolean;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <textarea
        aria-label={label}
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function TargetList({
  disabled,
  label,
  items,
  onChange,
}: {
  disabled: boolean;
  label: string;
  items: readonly string[];
  onChange: (items: string[]) => void;
}) {
  if (!items.length) return null;
  return (
    <fieldset className="practice-target-list">
      <legend>{label}</legend>
      {items.map((value, index) => (
        <TextField
          key={index}
          disabled={disabled}
          label={`${label} ${index + 1}`}
          value={value}
          onChange={(next) =>
            onChange(items.map((item, itemIndex) => (itemIndex === index ? next : item)))
          }
        />
      ))}
    </fieldset>
  );
}
