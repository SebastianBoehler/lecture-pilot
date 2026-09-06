import { ArrowRight } from "lucide-react";
import { useI18n } from "./i18n";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

export function OutlineProgress({
  state,
  onJumpAnchor,
}: {
  state: LearnerLessonState | null;
  onJumpAnchor: (id: string) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="outline-progress">
      {state?.active_session_goal ? (
        <p className="outline-goal">
          <span>{t("outline.learningGoal")}</span>
          {state.active_session_goal}
        </p>
      ) : null}
      {state?.pending_check ? (
        <button
          className="outline-continue"
          type="button"
          onClick={() => onJumpAnchor(state.pending_check!.gate_id)}
        >
          {t("outline.continue")}
          <ArrowRight size={15} aria-hidden="true" />
        </button>
      ) : null}
      <details className="outline-help">
        <summary>{t("outline.howPracticeWorks")}</summary>
        <p>{t("outline.navigationHelp")}</p>
        <ol>
          <li>{t("outline.practice.try")}</li>
          <li>{t("outline.practice.support")}</li>
          <li>{t("outline.practice.independent")}</li>
          <li>{t("outline.practice.review")}</li>
        </ol>
        <p>{t("outline.attemptAccess")}</p>
      </details>
    </div>
  );
}
