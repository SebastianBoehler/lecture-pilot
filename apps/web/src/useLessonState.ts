import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

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
  const activeKey = useRef(key);
  const requestVersions = useRef(new Map<string, number>());

  useLayoutEffect(() => {
    activeKey.current = key;
  }, [key]);

  const refresh = useCallback(async () => {
    if (activeKey.current !== key) return;
    if (!key || !session || mode === "draft") {
      setSnapshot({ key, data: null, loading: false, error: null });
      return;
    }
    const version = (requestVersions.current.get(key) ?? 0) + 1;
    requestVersions.current.set(key, version);
    setSnapshot((current) => ({
      key,
      data: current.key === key ? current.data : null,
      loading: true,
      error: null,
    }));
    try {
      const data = await getLearnerLessonState(courseId, lectureId, session, mode);
      if (activeKey.current === key && requestVersions.current.get(key) === version) {
        setSnapshot({ key, data, loading: false, error: null });
      }
    } catch (error) {
      if (activeKey.current === key && requestVersions.current.get(key) === version) {
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
    const versions = requestVersions.current;
    void refresh();
    return () => {
      if (key) versions.set(key, (versions.get(key) ?? 0) + 1);
    };
  }, [key, refresh]);

  const applyTutorResult = useCallback(async (_result: TutorStateUpdate) => refresh(), [refresh]);

  const applyQuizResult = useCallback(
    async (_result: LearnerQuizAnswerResult) => refresh(),
    [refresh],
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
