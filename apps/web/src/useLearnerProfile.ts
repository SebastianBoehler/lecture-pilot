import { useCallback, useEffect, useState } from "react";

import {
  clearLearnerMemory,
  getLearnerProfile,
  removeLearnerPreference,
  saveLearnerCalibration,
} from "./learnerProfileApi";
import type { LearnerProfile, LearningGoal, LoginSession } from "./types";

export type LearnerProfileState = {
  profile: LearnerProfile | null;
  loading: boolean;
  error: string | null;
  saveCalibration: (goal: LearningGoal) => Promise<void>;
  removePreference: (key: string) => Promise<void>;
  clearMemory: (courseId?: string) => Promise<void>;
  refresh: () => Promise<void>;
};

export function useLearnerProfile(
  session: LoginSession | null,
  enabled: boolean,
): LearnerProfileState {
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session || !enabled) return;
    setLoading(true);
    setError(null);
    try {
      setProfile(await getLearnerProfile(session));
    } catch (nextError) {
      setError(message(nextError));
    } finally {
      setLoading(false);
    }
  }, [enabled, session]);

  useEffect(() => {
    if (!enabled) {
      setProfile(null);
      setLoading(false);
      setError(null);
      return;
    }
    void refresh();
  }, [enabled, refresh]);

  async function mutate(action: () => Promise<unknown>) {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const result = await action();
      if (result) setProfile(result as LearnerProfile);
      else setProfile(await getLearnerProfile(session));
    } catch (nextError) {
      setError(message(nextError));
      throw nextError;
    } finally {
      setLoading(false);
    }
  }

  return {
    profile,
    loading,
    error,
    saveCalibration: (goal) => mutate(() => saveLearnerCalibration(session!, goal)),
    removePreference: (key) => mutate(() => removeLearnerPreference(session!, key)),
    clearMemory: (courseId) => mutate(() => clearLearnerMemory(session!, courseId)),
    refresh,
  };
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "Learning profile request failed.";
}
