import { useI18n } from "./i18n";
import type { LearningIntent } from "./learningIntentTypes";
import type { PracticeDesign } from "./practiceDesignTypes";

type Goal = LearningIntent["goals"][number];

export function ProfessorLearningGoalEditor({
  draft,
  target,
  disabled,
  onChange,
  onRemove,
}: {
  draft: PracticeDesign;
  target: Goal;
  disabled: boolean;
  onChange: (design: PracticeDesign) => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const goals = draft.learning_intent?.goals ?? draft.targets;
  function update(changes: Partial<Pick<Goal, "title" | "outcome">>) {
    onChange(
      draft.learning_intent
        ? {
            ...draft,
            learning_intent: {
              ...draft.learning_intent,
              goals: goals.map((goal) => (goal.id === target.id ? { ...goal, ...changes } : goal)),
            },
          }
        : {
            ...draft,
            targets: draft.targets.map((goal) =>
              goal.id === target.id ? { ...goal, ...changes } : goal,
            ),
          },
    );
  }
  function remove() {
    if (goals.length <= 1) return;
    onChange({
      ...draft,
      targets: draft.targets.filter(({ id }) => id !== target.id),
      ...(draft.learning_intent
        ? {
            learning_intent: {
              ...draft.learning_intent,
              goals: goals.filter(({ id }) => id !== target.id),
              fixed_targets: draft.learning_intent.fixed_targets.filter(
                ({ id }) => id !== target.id,
              ),
            },
          }
        : {}),
    });
    onRemove();
  }
  return (
    <div className="practice-target-fields">
      <label>
        {t("builder.intent.goalTitle", { target: target.title })}
        <input
          value={target.title}
          maxLength={200}
          disabled={disabled}
          onChange={(event) => update({ title: event.target.value })}
        />
      </label>
      <label>
        {t("builder.design.outcomeFor", { target: target.title })}
        <textarea
          value={target.outcome}
          maxLength={1000}
          disabled={disabled}
          onChange={(event) => update({ outcome: event.target.value })}
        />
      </label>
      <button type="button" disabled={disabled || goals.length <= 1} onClick={remove}>
        {t("builder.intent.deleteGoal", { target: target.title })}
      </button>
      {goals.length <= 1 ? <p>{t("builder.intent.minimumGoal")}</p> : null}
    </div>
  );
}
