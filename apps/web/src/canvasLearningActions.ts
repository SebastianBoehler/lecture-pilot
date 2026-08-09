import type { LearnerQuizAnswerResult } from "./analyticsApi";
import type { LearnerQuizState } from "./learnerLessonStateTypes";
import type { CanvasBlock } from "./types";

export type TutorMessageOptions = {
  checkpointGateId?: string;
  focusedSectionId?: string;
};

export type CanvasLearningActions = {
  publicationVersion: number | null;
  quizStates: Record<string, LearnerQuizState>;
  onSubmitQuizAnswer: (
    block: CanvasBlock,
    answer: string,
    optionIndex: number,
    attemptId: string,
    publicationVersion: number,
  ) => Promise<LearnerQuizAnswerResult>;
  onSubmitCheckpoint: (gateId: string, sectionId: string, answer: string) => Promise<void>;
};
