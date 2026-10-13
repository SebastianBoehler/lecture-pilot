import { useState } from "react";

import { publishLectureCanvas } from "../shared/api";
import { errorMessage } from "../shared/errorMessage";
import type { LoginSession } from "../shared/types";
import { keepLearningGoals, startLectureDraft } from "./courseLectureStatesApi";
import type { DiffGoal } from "./goalDiff";
import { getLearningDesignReview, learningDesignApprovalInput } from "./learningDesignApi";
import { proposePracticeDesign } from "./practiceDesignApi";

export type LecturePending = "drafting" | "keeping" | "regenerating" | "publishing";

/** Per-lecture actions of the course page; each failure stays on its own lecture row. */
export function useCourseLectureActions(input: {
  courseId: string;
  session: LoginSession;
  refresh: () => Promise<void>;
  onPublished: (lectureId: string) => void;
}) {
  const { courseId, session, refresh } = input;
  const [pending, setPending] = useState<Readonly<Record<string, LecturePending>>>({});
  const [errors, setErrors] = useState<Readonly<Record<string, string>>>({});
  const [previousGoals, setPreviousGoals] = useState<Readonly<Record<string, readonly DiffGoal[]>>>(
    {},
  );

  async function track(lectureId: string, kind: LecturePending, work: () => Promise<void>) {
    setPending((current) => ({ ...current, [lectureId]: kind }));
    setErrors((current) => without(current, lectureId));
    try {
      await work();
      return true;
    } catch (cause) {
      setErrors((current) => ({ ...current, [lectureId]: errorMessage(cause, fallback[kind]) }));
      return false;
    } finally {
      setPending((current) => without(current, lectureId));
      await refresh();
    }
  }

  const startDraft = (lectureId: string) =>
    track(lectureId, "drafting", () => startLectureDraft(courseId, lectureId, session));

  async function publish(lectureId: string) {
    return track(lectureId, "publishing", async () => {
      // Approve & publish exactly the reviewed draft revisions the backend reports now.
      const review = await getLearningDesignReview(courseId, lectureId, session);
      await publishLectureCanvas(courseId, lectureId, session, learningDesignApprovalInput(review));
      input.onPublished(lectureId);
    });
  }

  return {
    pending,
    errors,
    previousGoals,
    startDraft,
    publish,
    /** After goals are approved the lecture drafts right away, as in the course builder. */
    goalsApproved: startDraft,
    keepGoals: async (lectureId: string) => {
      const kept = await track(lectureId, "keeping", async () => {
        await keepLearningGoals(courseId, lectureId, session);
      });
      if (kept) await startDraft(lectureId);
    },
    regenerateGoals: (lectureId: string, previous: readonly DiffGoal[]) =>
      track(lectureId, "regenerating", async () => {
        setPreviousGoals((current) => ({ ...current, [lectureId]: previous }));
        await proposePracticeDesign({ courseId, lectureId, refresh: true, session });
      }),
    publishAll: async (lectureIds: readonly string[]) => {
      for (const lectureId of lectureIds) await publish(lectureId);
    },
  };
}

const fallback: Record<LecturePending, string> = {
  drafting: "Draft generation could not be started.",
  keeping: "Learning goals could not be kept.",
  regenerating: "Learning goals could not be regenerated.",
  publishing: "Publishing failed.",
};

function without<T>(record: Readonly<Record<string, T>>, key: string) {
  const next = { ...record };
  delete next[key];
  return next;
}
