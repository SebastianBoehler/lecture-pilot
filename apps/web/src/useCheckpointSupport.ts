import { useState } from "react";
import { requestCheckpointSupport } from "./learnerLessonStateApi";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { LearnerWorkspaceMode, LoginSession } from "./types";

export function useCheckpointSupport(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  mode: LearnerWorkspaceMode,
  state: LearnerLessonState | null,
) {
  const [replacement, setReplacement] = useState<{
    base: LearnerLessonState | null;
    value: LearnerLessonState;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = replacement?.base === state ? replacement.value : state;
  async function requestHelp() {
    if (busy || !current?.pending_check) return;
    setBusy(true);
    setError(null);
    try {
      const value = await requestCheckpointSupport(
        courseId,
        lectureId,
        session,
        mode,
        current.pending_check,
      );
      setReplacement({ base: state, value });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Help could not be recorded.");
    } finally {
      setBusy(false);
    }
  }
  return { state: current, requestHelp, busy, error };
}
