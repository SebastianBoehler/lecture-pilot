import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { MessageKey } from "./i18nMessages";

export function practiceStatus(
  type: string,
  id: string,
  state: LearnerLessonState | null,
): MessageKey {
  if (type === "quiz") {
    const quiz = state?.quiz_states[id];
    return quiz?.correct === true
      ? "outline.correct"
      : quiz?.correct === false
        ? "outline.reviewAnswer"
        : quiz
          ? "outline.answered"
          : "outline.kind.quiz";
  }
  const evidence = state?.goal_evidence?.find((item) => item.gate_id === id);
  if (evidence?.delayed) return "outline.delayed";
  if (evidence?.independent) return "outline.independent";
  if (evidence?.supported) return "outline.supported";
  if (state?.gate_statuses[id] === "passed") return "outline.passed";
  if (state?.gate_statuses[id] === "needs_evidence") return "outline.keepPractising";
  return "outline.kind.gate";
}
