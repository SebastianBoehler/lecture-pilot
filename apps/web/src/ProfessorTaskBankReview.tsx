import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
import type { SupplementalPracticeTask } from "./practiceTaskBankTypes";

export function ProfessorTaskBankReview({ tasks }: { tasks: readonly SupplementalPracticeTask[] }) {
  const { t } = useI18n();
  if (!tasks.length) return null;
  const symbols = { add: "+", subtract: "−", multiply: "×", divide: "÷" };
  return (
    <details className="practice-target-diagnostics">
      <summary>{t("review.taskBank.title", { count: tasks.length })}</summary>
      <p>{t("review.taskBank.help")}</p>
      {tasks.map((task) => (
        <section key={task.id}>
          <h4>
            {t(
              task.stage === "independent_exit"
                ? "review.taskBank.independent"
                : "review.taskBank.delayed",
            )}
          </h4>
          <MathText highlightedText={null} mode="block" text={task.prompt} />
          <p>
            <strong>{t("review.taskBank.surface")}</strong> {task.surface_change}
          </p>
          <ProfessorPracticeEvidence anchor={task.source_anchor} />
          {task.numeric_assertions.length ? (
            <ul aria-label={t("review.taskBank.numeric")}>
              {task.numeric_assertions.map((check, index) => (
                <li key={index}>
                  {check.operands.join(` ${symbols[check.operation]} `)} = {check.expected} (
                  {t("review.taskBank.tolerance", { value: check.tolerance })})
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}
    </details>
  );
}
