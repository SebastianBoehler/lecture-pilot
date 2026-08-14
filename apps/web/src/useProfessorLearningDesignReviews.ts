import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";

import {
  approveLearningDesignReview,
  getLearningDesignReview,
  saveLearningDesignReview,
} from "./learningDesignApi";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import type { LoginSession } from "./types";

type OperationToken = { epoch: number; key: string; operation: number };
type KeyedReviews = { key: string; values: Record<string, LearningDesignReview> };
type KeyedError = { key: string; message: string | null };
type KeyedPending = { count: number; key: string };

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
  const lectureKey = JSON.stringify(lectureIds);
  const identityKey = courseId
    ? JSON.stringify([session.tenant_id ?? "", session.username, courseId, lectureIds, revisionKey])
    : "";
  const active = useRef({ epoch: 0, key: identityKey, operation: 0 });
  const [reviewState, setReviewState] = useState<KeyedReviews>({ key: "", values: {} });
  const [errorState, setErrorState] = useState<KeyedError>({ key: "", message: null });
  const [pending, setPending] = useState<KeyedPending>({ count: 0, key: "" });
  const reviews = reviewState.key === identityKey ? reviewState.values : {};

  useLayoutEffect(() => {
    if (active.current.key !== identityKey) {
      active.current = {
        epoch: active.current.epoch + 1,
        key: identityKey,
        operation: 0,
      };
    }
  }, [identityKey]);

  useEffect(() => {
    if (!courseId || !identityKey) return;
    const token = beginOperation(active, identityKey);
    const activeLectureIds = JSON.parse(lectureKey) as string[];
    setErrorState({ key: identityKey, message: null });
    void Promise.all(
      activeLectureIds.map(
        async (lectureId) =>
          [lectureId, await getLearningDesignReview(courseId, lectureId, session)] as const,
      ),
    )
      .then((entries) => {
        if (isCurrent(active, token)) {
          setReviewState({ key: identityKey, values: Object.fromEntries(entries) });
        }
      })
      .catch((loadError) => {
        if (isCurrent(active, token)) {
          setErrorState({ key: identityKey, message: errorMessage(loadError) });
        }
      });
  }, [courseId, identityKey, lectureKey, session]);

  async function save(lectureId: string, update: LearningDesignUpdate) {
    if (!courseId || !identityKey) return;
    await mutate(() => saveLearningDesignReview(courseId, lectureId, session, update));
  }

  async function approve(lectureId: string) {
    if (!courseId || !identityKey) return;
    const review = reviews[lectureId];
    if (!review) return;
    await mutate(() => approveLearningDesignReview(courseId, lectureId, session, review));
  }

  async function mutate(operation: () => Promise<LearningDesignReview>) {
    const token = beginOperation(active, identityKey);
    setPending((current) => ({
      count: current.key === identityKey ? current.count + 1 : 1,
      key: identityKey,
    }));
    setErrorState({ key: identityKey, message: null });
    try {
      const changed = await operation();
      if (isCurrent(active, token)) {
        setReviewState((current) => ({
          key: identityKey,
          values: {
            ...(current.key === identityKey ? current.values : {}),
            [changed.lecture_id]: changed,
          },
        }));
      }
    } catch (mutationError) {
      if (isCurrent(active, token)) {
        setErrorState({ key: identityKey, message: errorMessage(mutationError) });
      }
    } finally {
      setPending((current) =>
        current.key === identityKey
          ? { key: identityKey, count: Math.max(0, current.count - 1) }
          : current,
      );
    }
  }

  const allApproved =
    Boolean(identityKey) &&
    reviewState.key === identityKey &&
    lectureIds.length > 0 &&
    lectureIds.every((lectureId) => reviewState.values[lectureId]?.approval);
  return {
    allApproved,
    approve,
    error: errorState.key === identityKey ? errorState.message : null,
    reviews,
    save,
    saving: pending.key === identityKey && pending.count > 0,
  };
}

function beginOperation(
  active: RefObject<{ epoch: number; key: string; operation: number }>,
  key: string,
): OperationToken {
  active.current.operation += 1;
  return { epoch: active.current.epoch, key, operation: active.current.operation };
}

function isCurrent(
  active: RefObject<{ epoch: number; key: string; operation: number }>,
  token: OperationToken,
): boolean {
  return (
    active.current.key === token.key &&
    active.current.epoch === token.epoch &&
    active.current.operation === token.operation
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Learning-design review failed.";
}
