import { useLayoutEffect, useRef, useState } from "react";

import {
  PracticeDesignRequestError,
  approvePracticeDesign,
  getPracticeDesign,
  proposePracticeDesign,
  reviewPracticeDesign,
  updatePracticeDesign,
} from "./practiceDesignApi";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";
import type { LoginSession } from "./types";

type State = {
  absent: Readonly<Record<string, true>>;
  designs: Readonly<Record<string, PracticeDesign>>;
  key: string;
};
export type PracticeDesignPendingAction =
  "load" | "propose" | "refresh" | "save" | "review" | "approve";
type PendingEntry = { action: PracticeDesignPendingAction; operation: number };
type Pending = { key: string; values: Readonly<Record<string, PendingEntry>> };
type ErrorState = { key: string; message: string | null };
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
  const [state, setState] = useState<State>({ absent: {}, designs: {}, key: "" });
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

  async function load(lectureId: string) {
    const token = begin(lectureId);
    markPending(token, true, "load");
    try {
      const design = await getPracticeDesign({ courseId: courseId!, lectureId, session });
      if (current(token)) setDesign(lectureId, design, false);
    } catch (loadError) {
      if (current(token)) {
        if (loadError instanceof PracticeDesignRequestError && loadError.status === 404) {
          setDesign(lectureId, null, true);
        } else {
          setErrorState({ key: identityKey, message: errorMessage(loadError) });
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
    setErrorState({ key: identityKey, message: null });
    try {
      const design = await operation();
      if (current(token)) setDesign(lectureId, design, false);
    } catch (mutationError) {
      if (current(token)) {
        setErrorState({ key: identityKey, message: errorMessage(mutationError) });
        if (mutationError instanceof PracticeDesignRequestError && mutationError.status === 409) {
          await load(lectureId);
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

  function setDesign(lectureId: string, design: PracticeDesign | null, absent: boolean) {
    setState((currentState) => {
      const currentDesigns = currentState.key === identityKey ? currentState.designs : {};
      const currentAbsent = currentState.key === identityKey ? currentState.absent : {};
      return {
        key: identityKey,
        designs: design
          ? { ...currentDesigns, [lectureId]: design }
          : omit(currentDesigns, [lectureId]),
        absent: absent ? { ...currentAbsent, [lectureId]: true } : omit(currentAbsent, [lectureId]),
      };
    });
  }

  async function loadAll(lectureIds: readonly string[]) {
    if (!courseId || !identityKey) return;
    setErrorState({ key: identityKey, message: null });
    await Promise.all(lectureIds.map((lectureId) => load(lectureId)));
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

  async function approve(lectureId: string) {
    const design = designs[lectureId];
    if (!courseId || !identityKey || !design) return;
    await mutate(lectureId, "approve", () =>
      approvePracticeDesign({ courseId, lectureId, design, session }),
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
      setState({ key: identityKey, designs: {}, absent: {} });
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
        const design = designs[lectureId];
        return Boolean(
          design?.approval &&
          design.approval.source_revision === design.source_revision &&
          design.approval.practice_design_revision === design.revision,
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
    loadAll,
    pendingAction: currentPending?.action ?? null,
    pendingLectureId: currentPending?.lectureId ?? null,
    propose,
    review,
    reset,
    save,
  };
}

function omit<T>(values: Readonly<Record<string, T>>, keys: readonly string[]): Record<string, T> {
  const next = { ...values };
  for (const key of keys) delete next[key];
  return next;
}

function latestPending(
  pending: Pending,
  key: string,
): (PendingEntry & { lectureId: string }) | null {
  if (pending.key !== key) return null;
  return Object.entries(pending.values).reduce<(PendingEntry & { lectureId: string }) | null>(
    (latest, [lectureId, entry]) =>
      !latest || entry.operation > latest.operation ? { lectureId, ...entry } : latest,
    null,
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Practice design request failed.";
}
