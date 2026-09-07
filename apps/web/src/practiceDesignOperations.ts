import type { PracticeDesignPendingAction } from "./useProfessorPracticeDesigns";

export type PendingEntry = { action: PracticeDesignPendingAction; operation: number };
export type Pending = { key: string; values: Readonly<Record<string, PendingEntry>> };

export function omit<T>(
  values: Readonly<Record<string, T>>,
  keys: readonly string[],
): Record<string, T> {
  const next = { ...values };
  for (const key of keys) delete next[key];
  return next;
}

export function latestPending(
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

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Practice design request failed.";
}

export type ErrorState = {
  key: string;
  message: string | null;
  byLecture?: Readonly<Record<string, string>>;
};
export function clearLectureError(current: ErrorState, key: string, lectureId: string): ErrorState {
  const byLecture = omit(current.key === key ? (current.byLecture ?? {}) : {}, [lectureId]);
  return { key, byLecture, message: Object.values(byLecture).at(-1) ?? null };
}
export function lectureError(
  current: ErrorState,
  key: string,
  lectureId: string,
  error: unknown,
): ErrorState {
  const message = errorMessage(error);
  return {
    key,
    message,
    byLecture: { ...(current.key === key ? current.byLecture : {}), [lectureId]: message },
  };
}
