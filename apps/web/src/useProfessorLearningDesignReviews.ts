import { runBoundedTasks } from "./boundedTaskPool";
import {
  useEffect,
  useEffectEvent,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from "react";

import {
  approveLearningDesignReview,
  getLearningDesignReview,
  saveLearningDesignReview,
} from "./learningDesignApi";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import type { LoginSession } from "./types";

type OperationToken = { epoch: number; key: string; lectureId: string; operation: number };
type Active = { epoch: number; key: string; operations: Record<string, number> };
type KeyedReviews = { key: string; values: Record<string, LearningDesignReview> };
type KeyedError = { key: string; message: string | null; byLecture?: Record<string, string> };
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
  const active = useRef<Active>({ epoch: 0, key: identityKey, operations: {} });
  const [reviewState, setReviewState] = useState<KeyedReviews>({ key: "", values: {} });
  const [errorState, setErrorState] = useState<KeyedError>({ key: "", message: null });
  const [pending, setPending] = useState<KeyedPending>({ count: 0, key: "" });
  const reviews = reviewState.key === identityKey ? reviewState.values : {};

  useLayoutEffect(() => {
    if (active.current.key !== identityKey) {
      active.current = {
        epoch: active.current.epoch + 1,
        key: identityKey,
        operations: {},
      };
    }
  }, [identityKey]);

  const load = useEffectEvent((ids: string[]) => runBoundedTasks(ids, 4, reload));

  useEffect(() => {
    if (!courseId || !identityKey) return;
    const activeLectureIds = JSON.parse(lectureKey) as string[];
    setErrorState({ key: identityKey, message: null });
    void load(activeLectureIds);
    return () => {
      active.current.epoch += 1;
    };
  }, [courseId, identityKey, lectureKey, session]);

  async function reload(lectureId: string) {
    if (!courseId || !identityKey) return;
    const token = beginOperation(active, identityKey, lectureId);
    setErrorState((current) => {
      const byLecture = { ...(current.key === identityKey ? current.byLecture : {}) };
      delete byLecture[lectureId];
      return { key: identityKey, message: null, byLecture };
    });
    try {
      const review = await getLearningDesignReview(courseId, lectureId, session);
      if (isCurrent(active, token))
        setReviewState((current) => ({
          key: identityKey,
          values: { ...(current.key === identityKey ? current.values : {}), [lectureId]: review },
        }));
    } catch (error) {
      if (isCurrent(active, token))
        setErrorState((current) => ({
          key: identityKey,
          message: errorMessage(error),
          byLecture: {
            ...(current.key === identityKey ? current.byLecture : {}),
            [lectureId]: errorMessage(error),
          },
        }));
    }
  }

  async function save(lectureId: string, update: LearningDesignUpdate) {
    if (!courseId || !identityKey) return;
    await mutate(lectureId, () => saveLearningDesignReview(courseId, lectureId, session, update));
  }

  async function approve(lectureId: string) {
    if (!courseId || !identityKey) return;
    const review = reviews[lectureId];
    if (!review) return;
    await mutate(lectureId, () =>
      approveLearningDesignReview(courseId, lectureId, session, review),
    );
  }

  async function mutate(lectureId: string, operation: () => Promise<LearningDesignReview>) {
    const token = beginOperation(active, identityKey, lectureId);
    setPending((current) => ({
      count: current.key === identityKey ? current.count + 1 : 1,
      key: identityKey,
    }));
    setErrorState((current) => {
      const byLecture = { ...(current.key === identityKey ? current.byLecture : {}) };
      delete byLecture[lectureId];
      return { key: identityKey, message: null, byLecture };
    });
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
        setErrorState((current) => ({
          key: identityKey,
          message: errorMessage(mutationError),
          byLecture: {
            ...(current.key === identityKey ? current.byLecture : {}),
            [lectureId]: errorMessage(mutationError),
          },
        }));
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
    errorsByLecture: errorState.key === identityKey ? (errorState.byLecture ?? {}) : {},
    reload,
    save,
    saving: pending.key === identityKey && pending.count > 0,
  };
}

function beginOperation(active: RefObject<Active>, key: string, lectureId: string): OperationToken {
  const operation = (active.current.operations[lectureId] ?? 0) + 1;
  active.current.operations[lectureId] = operation;
  return { epoch: active.current.epoch, key, lectureId, operation };
}

function isCurrent(active: RefObject<Active>, token: OperationToken): boolean {
  return (
    active.current.key === token.key &&
    active.current.epoch === token.epoch &&
    active.current.operations[token.lectureId] === token.operation
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Learning-design review failed.";
}
