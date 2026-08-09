import { useEffect, useState } from "react";

import {
  approveLearningDesignReview,
  getLearningDesignReview,
  saveLearningDesignReview,
} from "./learningDesignApi";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import type { LoginSession } from "./types";

export function useProfessorLearningDesignReviews({
  courseId,
  lectureIds,
  revisionKey,
  session,
}: {
  courseId: string | null;
  lectureIds: string[];
  revisionKey: string;
  session: LoginSession;
}) {
  const [reviews, setReviews] = useState<Record<string, LearningDesignReview>>({});
  const [savingCount, setSavingCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const lectureKey = lectureIds.join("|");

  useEffect(() => {
    let cancelled = false;
    if (!courseId || !lectureKey) {
      setReviews({});
      setError(null);
      return;
    }
    setReviews({});
    setError(null);
    const activeLectureIds = lectureKey.split("|");
    void Promise.all(
      activeLectureIds.map(
        async (lectureId) =>
          [lectureId, await getLearningDesignReview(courseId, lectureId, session)] as const,
      ),
    )
      .then((entries) => {
        if (!cancelled) setReviews(Object.fromEntries(entries));
      })
      .catch((loadError) => {
        if (!cancelled)
          setError(
            loadError instanceof Error ? loadError.message : "Learning-design review failed.",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, lectureKey, revisionKey, session]);

  async function save(lectureId: string, update: LearningDesignUpdate) {
    if (!courseId) return;
    await mutate(() => saveLearningDesignReview(courseId, lectureId, session, update));
  }

  async function approve(lectureId: string) {
    if (!courseId) return;
    const review = reviews[lectureId];
    if (!review) return;
    await mutate(() => approveLearningDesignReview(courseId, lectureId, session, review));
  }

  async function mutate(operation: () => Promise<LearningDesignReview>) {
    setSavingCount((count) => count + 1);
    setError(null);
    try {
      const changed = await operation();
      setReviews((current) => ({ ...current, [changed.lecture_id]: changed }));
    } catch (mutationError) {
      setError(
        mutationError instanceof Error ? mutationError.message : "Learning-design review failed.",
      );
    } finally {
      setSavingCount((count) => count - 1);
    }
  }

  const allApproved =
    Boolean(lectureKey) && lectureKey.split("|").every((lectureId) => reviews[lectureId]?.approval);
  return {
    allApproved,
    approve,
    error,
    reviews,
    save,
    saving: savingCount > 0,
  };
}
