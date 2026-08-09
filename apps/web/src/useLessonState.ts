import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getLearnerLessonState } from "./learnerLessonStateApi";
import type { LearnerQuizAnswerResult } from "./analyticsApi";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { LessonMode, LoginSession } from "./types";

type Snapshot = {
  key: string;
  data: LearnerLessonState | null;
  loading: boolean;
  error: string | null;
};

type TutorStateUpdate = {
  session_goal?: string | null;
  quality_gate?: {
    gate_id: string;
    status: "passed" | "needs_evidence" | "not_assessed";
  } | null;
};

export function useLessonState({
  courseId,
  lectureId,
  session,
  mode,
  enabled,
}: {
  courseId: string;
  lectureId: string;
  session: LoginSession | null;
  mode: LessonMode;
  enabled: boolean;
}) {
  const key =
    enabled && session && mode !== "draft"
      ? JSON.stringify([mode, session.tenant_id ?? "", session.username, courseId, lectureId])
      : "";
  const [snapshot, setSnapshot] = useState<Snapshot>({
    key: "",
    data: null,
    loading: false,
    error: null,
  });
  const requestVersion = useRef(0);

  const refresh = useCallback(async () => {
    const version = ++requestVersion.current;
    if (!key || !session || mode === "draft") {
      setSnapshot({ key, data: null, loading: false, error: null });
      return;
    }
    setSnapshot((current) => ({
      key,
      data: current.key === key ? current.data : null,
      loading: true,
      error: null,
    }));
    try {
      const data = await getLearnerLessonState(courseId, lectureId, session, mode);
      if (requestVersion.current === version) {
        setSnapshot({ key, data, loading: false, error: null });
      }
    } catch (error) {
      if (requestVersion.current === version) {
        setSnapshot({
          key,
          data: null,
          loading: false,
          error: error instanceof Error ? error.message : "Learner state loading failed.",
        });
      }
    }
  }, [courseId, key, lectureId, mode, session]);

  useEffect(() => {
    void refresh();
    return () => {
      requestVersion.current += 1;
    };
  }, [refresh]);

  const applyTutorResult = useCallback(
    (result: TutorStateUpdate) => {
      if (!key) return;
      requestVersion.current += 1;
      setSnapshot((current) => {
        const data = current.key === key ? current.data : null;
        const gate = result.quality_gate;
        return {
          key,
          loading: false,
          error: null,
          data: {
            course_id: courseId,
            lecture_id: lectureId,
            gate_statuses: {
              ...(data?.gate_statuses ?? {}),
              ...(gate ? { [gate.gate_id]: gate.status } : {}),
            },
            quiz_states: data?.quiz_states ?? {},
            active_session_goal: result.session_goal ?? data?.active_session_goal ?? null,
            pending_check: data?.pending_check ?? null,
            due_gate_reviews: data?.due_gate_reviews ?? [],
          },
        };
      });
    },
    [courseId, key, lectureId],
  );

  const applyQuizResult = useCallback(
    (result: LearnerQuizAnswerResult) => {
      if (!key) return;
      requestVersion.current += 1;
      setSnapshot((current) => {
        const data = current.key === key ? current.data : null;
        return {
          key,
          loading: false,
          error: null,
          data: {
            course_id: courseId,
            lecture_id: lectureId,
            gate_statuses: data?.gate_statuses ?? {},
            quiz_states: {
              ...(data?.quiz_states ?? {}),
              [result.block_id]: {
                selected_index: result.selected_index,
                correct: result.correct,
              },
            },
            active_session_goal: data?.active_session_goal ?? null,
            pending_check: data?.pending_check ?? null,
            due_gate_reviews: data?.due_gate_reviews ?? [],
          },
        };
      });
    },
    [courseId, key, lectureId],
  );

  return useMemo(
    () => ({
      state: snapshot.key === key ? snapshot.data : null,
      loading: snapshot.key === key && snapshot.loading,
      error: snapshot.key === key ? snapshot.error : null,
      refresh,
      applyTutorResult,
      applyQuizResult,
    }),
    [applyQuizResult, applyTutorResult, key, refresh, snapshot],
  );
}
