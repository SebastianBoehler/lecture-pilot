import { runBoundedTasks } from "./boundedTaskPool";
import {
  lectureError,
  clearLectureError,
  type ErrorState,
  latestPending,
  omit,
  type Pending,
} from "./practiceDesignOperations";
import type { LearningIntentApprovalOptions } from "./learningIntentTypes";
import { useLayoutEffect, useRef, useState } from "react";

import {
  PracticeDesignRequestError,
  approvePracticeDesign,
  getPracticeDesign,
  getPracticeDesignReadiness,
  proposePracticeDesign,
  reviewPracticeDesign,
  updatePracticeDesign,
} from "./practiceDesignApi";
import type {
  PracticeDesign,
  PracticeDesignReadiness,
  PracticeDesignState,
  PracticeDesignUpdate,
} from "./practiceDesignTypes";
import { isPracticeDesignReady } from "./practiceDesignReadiness";
import type { LoginSession } from "./types";

export type PracticeDesignPendingAction =
  "load" | "propose" | "refresh" | "save" | "review" | "approve";

type Token = { epoch: number; key: string; lectureId: string; operation: number };
type Active = {
  epoch: number;
  key: string;
  nextOperation: number;
  operations: Record<string, number>;
};

export function useProfessorPracticeDesigns({
  courseId,
  session,
}: {
  courseId: string | null;
  session: LoginSession;
}) {
  const identityKey = courseId
    ? JSON.stringify([session.tenant_id ?? "", session.username, courseId])
    : "";
  const active = useRef<Active>({ epoch: 0, key: identityKey, nextOperation: 0, operations: {} });
  const [state, setState] = useState<PracticeDesignState>({
    absent: {},
    designs: {},
    key: "",
    readiness: {},
  });
  const [pending, setPending] = useState<Pending>({ key: "", values: {} });
  const [errorState, setErrorState] = useState<ErrorState>({ key: "", message: null });
  const designs = state.key === identityKey ? state.designs : {};

  useLayoutEffect(() => {
    if (active.current.key !== identityKey) {
      active.current = {
        epoch: active.current.epoch + 1,
        key: identityKey,
        nextOperation: 0,
        operations: {},
      };
    }
    return () => {
      active.current = {
        ...active.current,
        epoch: active.current.epoch + 1,
        operations: {},
      };
    };
  }, [identityKey]);

  async function load(lectureId: string, proposeMissing = false, preserveError = false) {
    let design: PracticeDesign | undefined;
    const token = begin(lectureId);
    markPending(token, true, "load");
    if (!preserveError)
      setErrorState((current) => clearLectureError(current, identityKey, lectureId));
    try {
      design = await getPracticeDesign({ courseId: courseId!, lectureId, session });
      if (current(token)) setDesign(lectureId, design, null, false);
      const readiness = await getPracticeDesignReadiness({
        courseId: courseId!,
        lectureId,
        session,
      });
      if (current(token)) setDesign(lectureId, design, readiness, false);
    } catch (loadError) {
      if (current(token)) {
        if (
          !design &&
          loadError instanceof PracticeDesignRequestError &&
          loadError.status === 404
        ) {
          setDesign(lectureId, null, null, true);
          if (proposeMissing) await propose(lectureId);
        } else {
          setErrorState((current) => lectureError(current, identityKey, lectureId, loadError));
        }
      }
    } finally {
      markPending(token, false, "load");
    }
  }

  async function mutate(
    lectureId: string,
    action: PracticeDesignPendingAction,
    operation: () => Promise<PracticeDesign>,
  ) {
    const token = begin(lectureId);
    markPending(token, true, action);
    setErrorState((current) => ({
      key: identityKey,
      message: null,
      byLecture: omit(current.key === identityKey ? (current.byLecture ?? {}) : {}, [lectureId]),
    }));
    try {
      const design = await operation();
      if (current(token)) setDesign(lectureId, design, null, false);
      const readiness = await getPracticeDesignReadiness({
        courseId: courseId!,
        lectureId,
        session,
      });
      if (current(token)) setDesign(lectureId, design, readiness, false);
    } catch (mutationError) {
      if (current(token)) {
        setErrorState((current) => lectureError(current, identityKey, lectureId, mutationError));
        if (mutationError instanceof PracticeDesignRequestError && mutationError.status === 409) {
          await load(lectureId, false, true);
        }
      }
    } finally {
      markPending(token, false, action);
    }
  }

  function begin(lectureId: string): Token {
    const operation = active.current.nextOperation + 1;
    active.current.nextOperation = operation;
    active.current.operations[lectureId] = operation;
    return { epoch: active.current.epoch, key: identityKey, lectureId, operation };
  }

  function current(token: Token): boolean {
    return (
      active.current.key === token.key &&
      active.current.epoch === token.epoch &&
      active.current.operations[token.lectureId] === token.operation
    );
  }

  function markPending(
    token: Token,
    activeOperation: boolean,
    action: PracticeDesignPendingAction,
  ) {
    if (!current(token)) return;
    setPending((currentPending) => {
      const currentValues = currentPending.key === token.key ? currentPending.values : {};
      const values = activeOperation
        ? { ...currentValues, [token.lectureId]: { action, operation: token.operation } }
        : currentValues[token.lectureId]?.operation === token.operation
          ? omit(currentValues, [token.lectureId])
          : currentValues;
      return { key: token.key, values };
    });
  }

  function setDesign(
    lectureId: string,
    design: PracticeDesign | null,
    readiness: PracticeDesignReadiness | null,
    absent: boolean,
  ) {
    setState((currentState) => {
      const currentDesigns = currentState.key === identityKey ? currentState.designs : {};
      const currentAbsent = currentState.key === identityKey ? currentState.absent : {};
      const currentReadiness = currentState.key === identityKey ? currentState.readiness : {};
      return {
        key: identityKey,
        designs: design
          ? { ...currentDesigns, [lectureId]: design }
          : omit(currentDesigns, [lectureId]),
        absent: absent ? { ...currentAbsent, [lectureId]: true } : omit(currentAbsent, [lectureId]),
        readiness: readiness
          ? { ...currentReadiness, [lectureId]: readiness }
          : omit(currentReadiness, [lectureId]),
      };
    });
  }

  async function loadAll(lectureIds: readonly string[], proposeMissing = false) {
    if (!courseId || !identityKey) return;
    setErrorState({ key: identityKey, message: null });
    await runBoundedTasks([...lectureIds], 4, (id) => load(id, proposeMissing));
  }

  async function propose(lectureId: string, refresh = false) {
    if (!courseId || !identityKey) return;
    await mutate(lectureId, refresh ? "refresh" : "propose", () =>
      proposePracticeDesign({ courseId, lectureId, refresh, session }),
    );
  }

  async function save(lectureId: string, update: PracticeDesignUpdate) {
    if (!courseId || !identityKey) return;
    await mutate(lectureId, "save", () =>
      updatePracticeDesign({ courseId, lectureId, session, update }),
    );
  }

  async function approve(lectureId: string, intent?: LearningIntentApprovalOptions) {
    const design = designs[lectureId];
    if (!courseId || !identityKey || !design) return;
    await mutate(lectureId, "approve", () =>
      approvePracticeDesign({ courseId, lectureId, design, session, intent }),
    );
  }

  async function review(lectureId: string) {
    const design = designs[lectureId];
    if (!courseId || !identityKey || !design) return;
    await mutate(lectureId, "review", () =>
      reviewPracticeDesign({ courseId, lectureId, design, session }),
    );
  }

  function reset(lectureIds?: readonly string[]) {
    if (!identityKey) return;
    if (!lectureIds) {
      active.current = {
        ...active.current,
        epoch: active.current.epoch + 1,
        operations: {},
      };
      setState({ key: identityKey, designs: {}, absent: {}, readiness: {} });
      setPending({ key: identityKey, values: {} });
      setErrorState({ key: identityKey, message: null });
      return;
    }
    const ids = [...lectureIds];
    for (const lectureId of ids) {
      active.current.nextOperation += 1;
      active.current.operations[lectureId] = active.current.nextOperation;
    }
    setState((current) => ({
      key: identityKey,
      designs: omit(current.key === identityKey ? current.designs : {}, ids),
      absent: omit(current.key === identityKey ? current.absent : {}, ids),
      readiness: omit(current.key === identityKey ? current.readiness : {}, ids),
    }));
    setPending((current) => ({
      key: identityKey,
      values: omit(current.key === identityKey ? current.values : {}, ids),
    }));
    setErrorState({ key: identityKey, message: null });
  }

  function allApproved(lectureIds: readonly string[]) {
    return (
      lectureIds.length > 0 &&
      lectureIds.every((lectureId) => {
        return Boolean(
          state.key === identityKey &&
          isPracticeDesignReady(designs[lectureId], state.readiness[lectureId]),
        );
      })
    );
  }

  const currentPending = latestPending(pending, identityKey);
  return {
    allApproved,
    approve,
    designs,
    error: errorState.key === identityKey ? errorState.message : null,
    errorsByLecture: errorState.key === identityKey ? (errorState.byLecture ?? {}) : {},
    loadAll,
    load,
    pendingByLecture: pending.key === identityKey ? pending.values : {},
    pendingAction: currentPending?.action ?? null,
    pendingLectureId: currentPending?.lectureId ?? null,
    readiness: state.key === identityKey ? state.readiness : {},
    propose,
    review,
    reset,
    save,
  };
}
