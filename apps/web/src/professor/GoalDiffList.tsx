import { useI18n } from "../i18n/i18n";
import type { GoalDiffEntry } from "./goalDiff";

/** Regenerated goals next to the goals approved before, so the professor sees what moved. */
export function GoalDiffList({ entries }: { entries: readonly GoalDiffEntry[] }) {
  const { t } = useI18n();
  if (!entries.length) return null;
  return (
    <section className="goal-diff" aria-labelledby="goal-diff-title">
      <h4 id="goal-diff-title">{t("coursePage.goalDiff.title")}</h4>
      <ul>
        {entries.map((entry, index) => {
          const goal = entry.after ?? entry.before;
          if (!goal) return null;
          const renamed = entry.kind === "changed" && entry.before?.title !== entry.after?.title;
          const outcomeChanged =
            entry.kind === "changed" && entry.before?.outcome !== entry.after?.outcome;
          return (
            <li key={`${entry.kind}-${goal.id}-${index}`} data-kind={entry.kind}>
              <span className="goal-diff-kind">{t(`coursePage.goalDiff.${entry.kind}`)}</span>
              <div>
                <strong>{goal.title}</strong>
                {renamed && entry.before ? (
                  <p className="goal-diff-before">
                    {t("coursePage.goalDiff.before", { title: entry.before.title })}
                  </p>
                ) : null}
                {outcomeChanged && entry.before ? (
                  <p className="goal-diff-outcome">
                    <del>{entry.before.outcome}</del>
                    <ins>{entry.after?.outcome}</ins>
                  </p>
                ) : (
                  <p className="goal-diff-outcome">{goal.outcome}</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
