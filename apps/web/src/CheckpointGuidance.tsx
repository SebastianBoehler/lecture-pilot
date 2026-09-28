import { createContext, useContext } from "react";
import { MathText } from "./MathText";
import { useI18n } from "./i18n";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

export const CheckpointGuidanceContext = createContext<LearnerLessonState | null>(null);

export function CheckpointGuidance({ gateId }: { gateId: string }) {
  const { t } = useI18n();
  const state = useContext(CheckpointGuidanceContext);
  const check = state?.pending_check;
  if (check?.focus_required) return null;
  const missing =
    state?.goal_evidence?.find((item) => item.gate_id === gateId)?.missing_evidence?.slice(0, 2) ??
    [];
  if ((!check || check.gate_id !== gateId) && !missing.length) return null;
  return (
    <div className="checkpoint-guidance">
      {missing.length ? (
        <div className="checkpoint-next-step">
          <strong>{t("checkpoint.nextStep")}</strong>
          <ul>
            {missing.map((item) => (
              <li key={item}>
                <MathText text={item} highlightedText={null} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {check?.gate_id === gateId && check.bank_exhausted ? (
        <p role="status">
          You can continue practising with help. A new reviewed task is needed for another
          independent attempt.
        </p>
      ) : null}
      {check?.gate_id === gateId && check.assistance_content ? (
        <details>
          <summary>Hint for this task</summary>
          <MathText text={check.assistance_content} mode="block" highlightedText={null} />
        </details>
      ) : null}
    </div>
  );
}
