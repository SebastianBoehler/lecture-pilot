import { createContext, useContext } from "react";
import { MathText } from "./MathText";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

export const CheckpointGuidanceContext = createContext<LearnerLessonState | null>(null);

export function CheckpointGuidance({ gateId }: { gateId: string }) {
  const check = useContext(CheckpointGuidanceContext)?.pending_check;
  if (!check || check.gate_id !== gateId || check.focus_required) return null;
  return (
    <div className="checkpoint-guidance">
      {check.bank_exhausted ? (
        <p role="status">
          You can continue practising with help. A new reviewed task is needed for another
          independent attempt.
        </p>
      ) : null}
      {check.assistance_content ? (
        <details>
          <summary>Hint for this task</summary>
          <MathText text={check.assistance_content} mode="block" highlightedText={null} />
        </details>
      ) : null}
    </div>
  );
}
