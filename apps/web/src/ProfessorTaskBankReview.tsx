import { MathText } from "./MathText";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
import type { SupplementalPracticeTask } from "./practiceTaskBankTypes";

export function ProfessorTaskBankReview({ tasks }: { tasks: readonly SupplementalPracticeTask[] }) {
  if (!tasks.length) return null;
  const symbols = { add: "+", subtract: "−", multiply: "×", divide: "÷" };
  return (
    <details className="practice-target-diagnostics">
      <summary>Fresh reviewed task variants ({tasks.length})</summary>
      <p>
        These tasks preserve the goal and rubric. Learners receive a fresh variant after support;
        future wording stays hidden from their learning path.
      </p>
      {tasks.map((task) => (
        <section key={task.id}>
          <h4>{task.stage === "independent_exit" ? "Independent check" : "Delayed review"}</h4>
          <MathText highlightedText={null} mode="block" text={task.prompt} />
          <p>
            <strong>Changed surface:</strong> {task.surface_change}
          </p>
          <ProfessorPracticeEvidence anchor={task.source_anchor} />
          {task.numeric_assertions.length ? (
            <ul aria-label="Numeric consistency checks">
              {task.numeric_assertions.map((check, index) => (
                <li key={index}>
                  {check.operands.join(` ${symbols[check.operation]} `)} = {check.expected}{" "}
                  (tolerance {check.tolerance})
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}
    </details>
  );
}
