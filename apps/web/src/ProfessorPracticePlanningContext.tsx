import { useId } from "react";

import { useI18n } from "./i18n";
import { TextField } from "./ProfessorPracticeEditorFields";
import type { PracticePlanningContext, PracticePlanningContextField } from "./practiceDesignTypes";

type Translator = ReturnType<typeof useI18n>["t"];

export function ProfessorPracticePlanningContext({
  context,
}: {
  context: PracticePlanningContext;
}) {
  const { t } = useI18n();
  const headingId = useId();
  const entries = [
    ["learnerLevel", context.learner_level],
    ["prerequisites", listValue(context.prerequisites, t("builder.design.noneSpecified"))],
    [
      "timeBudget",
      context.time_budget_minutes
        ? t("builder.design.minutes", { minutes: context.time_budget_minutes })
        : null,
    ],
    ["allowedAids", listValue(context.allowed_aids, t("builder.design.noAids"))],
    ["assessmentConditions", context.assessment_conditions],
  ] as const;
  return (
    <section className="practice-planning-context" aria-labelledby={headingId}>
      <h4 id={headingId}>{t("builder.design.planningContext")}</h4>
      <dl>
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt>{t(`builder.design.context.${key}`)}</dt>
            <dd>{value ?? t("builder.design.sourceInsufficient")}</dd>
          </div>
        ))}
      </dl>
      {context.insufficiencies.length ? (
        <details className="practice-context-gaps">
          <summary>{t("builder.design.contextGaps")}</summary>
          <ul>
            {context.insufficiencies.map((gap) => (
              <li key={gap.field}>{gap.description}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

export function ProfessorPracticePlanningContextEditor({
  context,
  onChange,
}: {
  context: PracticePlanningContext;
  onChange: (context: PracticePlanningContext) => void;
}) {
  const { t } = useI18n();
  return (
    <fieldset className="practice-context-editor">
      <legend>{t("builder.design.planningContext")}</legend>
      <TextField
        disabled={false}
        label={t("builder.design.context.learnerLevel")}
        value={context.learner_level ?? ""}
        onChange={(learner_level) =>
          onChange(withValue(context, "learner_level", learner_level.trim() || null, t))
        }
      />
      <TextField
        disabled={false}
        help={t("builder.design.onePerLine")}
        label={t("builder.design.context.prerequisites")}
        value={context.prerequisites?.join("\n") ?? ""}
        onChange={(value) => onChange(withValue(context, "prerequisites", lines(value), t))}
      />
      <label>
        {t("builder.design.context.timeBudget")}
        <input
          min="1"
          type="number"
          value={context.time_budget_minutes ?? ""}
          onChange={(event) =>
            onChange(
              withValue(
                context,
                "time_budget_minutes",
                event.target.value ? Number(event.target.value) : null,
                t,
              ),
            )
          }
        />
      </label>
      <TextField
        disabled={false}
        help={t("builder.design.onePerLine")}
        label={t("builder.design.context.allowedAids")}
        value={context.allowed_aids?.join("\n") ?? ""}
        onChange={(value) => onChange(withValue(context, "allowed_aids", lines(value), t))}
      />
      <TextField
        disabled={false}
        label={t("builder.design.context.assessmentConditions")}
        value={context.assessment_conditions ?? ""}
        onChange={(assessment_conditions) =>
          onChange(
            withValue(context, "assessment_conditions", assessment_conditions.trim() || null, t),
          )
        }
      />
      {context.insufficiencies.map((gap) => (
        <TextField
          disabled={false}
          key={gap.field}
          label={t("builder.design.contextGapFor", {
            field: t(`builder.design.context.${contextLabel(gap.field)}`),
          })}
          value={gap.description}
          onChange={(description) =>
            onChange({
              ...context,
              insufficiencies: context.insufficiencies.map((item) =>
                item.field === gap.field ? { ...item, description } : item,
              ),
            })
          }
        />
      ))}
    </fieldset>
  );
}

function lines(value: string): readonly string[] | null {
  const items = value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : null;
}

function listValue(value: readonly string[] | null, empty: string): string | null {
  return value ? (value.length ? value.join(", ") : empty) : null;
}

function withValue(
  context: PracticePlanningContext,
  field: PracticePlanningContextField,
  value: string | readonly string[] | number | null,
  t: Translator,
): PracticePlanningContext {
  const insufficiencies =
    value === null
      ? context.insufficiencies.some((item) => item.field === field)
        ? context.insufficiencies
        : [
            ...context.insufficiencies,
            { field, description: t("builder.design.professorUnspecified") },
          ]
      : context.insufficiencies.filter((item) => item.field !== field);
  return { ...context, [field]: value, insufficiencies } as PracticePlanningContext;
}

function contextLabel(
  field: PracticePlanningContextField,
): "learnerLevel" | "prerequisites" | "timeBudget" | "allowedAids" | "assessmentConditions" {
  return (
    {
      learner_level: "learnerLevel",
      prerequisites: "prerequisites",
      time_budget_minutes: "timeBudget",
      allowed_aids: "allowedAids",
      assessment_conditions: "assessmentConditions",
    } as const
  )[field];
}
