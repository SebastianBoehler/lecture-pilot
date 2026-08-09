import { useState } from "react";

import {
  recordQuizAnswer,
  StaleQuizPublicationError,
  type LearnerQuizAnswerResult,
} from "./analyticsApi";
import type { TutorMessageOptions } from "./canvasLearningActions";
import { useI18n } from "./i18n";
import { canonicalQuizId } from "./quizIdentity";
import type { CanvasBlock, LearnerWorkspaceMode, LoginSession, Lecture } from "./types";

export function useCanvasLearningAttempts({
  courseId,
  lecture,
  session,
  workspaceMode,
  openChat,
  onPracticeSubmitted,
  onSendMessage,
}: {
  courseId: string;
  lecture: Lecture;
  session: LoginSession;
  workspaceMode: LearnerWorkspaceMode;
  openChat: () => void;
  onPracticeSubmitted: (result: LearnerQuizAnswerResult) => void | Promise<void>;
  onSendMessage: (message: string, options?: TutorMessageOptions) => Promise<void>;
}) {
  const { t } = useI18n();
  const [coachingError, setCoachingError] = useState<string | null>(null);

  async function submitQuiz(
    block: CanvasBlock,
    answer: string,
    optionIndex: number,
    attemptId: string,
    publicationVersion: number,
  ) {
    let result;
    try {
      result = await recordQuizAnswer({
        courseId,
        lectureId: lecture.id,
        attendance: lecture.attendance,
        attemptId,
        blockId: canonicalQuizId(block),
        optionIndex,
        publicationVersion,
        session,
        mode: workspaceMode,
      });
    } catch (reason) {
      if (reason instanceof StaleQuizPublicationError) window.location.reload();
      throw reason;
    }
    await onPracticeSubmitted(result);
    openChat();
    setCoachingError(null);
    void onSendMessage(quizAnswerMessage(block, answer, optionIndex)).catch((reason) => {
      setCoachingError(errorMessage(reason, t("quiz.coachingFailed")));
    });
    return result;
  }

  async function submitCheckpoint(gateId: string, sectionId: string, answer: string) {
    openChat();
    setCoachingError(null);
    await onSendMessage(answer, { checkpointGateId: gateId, focusedSectionId: sectionId });
  }

  return { coachingError, submitCheckpoint, submitQuiz };
}

function quizAnswerMessage(block: CanvasBlock, answer: string, optionIndex: number) {
  const letter = String.fromCharCode(65 + optionIndex);
  const prompt = block.text?.trim();
  const title = block.caption?.trim() || "retrieval quiz";
  return [
    `Retrieval quiz answer for "${title}": ${letter}. ${answer}`,
    prompt ? `Question: ${prompt}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

function errorMessage(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}
