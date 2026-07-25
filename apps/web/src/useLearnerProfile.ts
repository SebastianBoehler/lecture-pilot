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

type CachedLearnerProfile = {
  owner: string;
  profile: LearnerProfile;
};

export function useLearnerProfile(
  session: LoginSession | null,
  enabled: boolean,
): LearnerProfileState {
  const owner = session
    ? `${session.tenant_id ?? "tenant-tuebingen"}:${session.username}:${session.csrf_token ?? "dev"}`
    : null;
  const [cached, setCached] = useState<CachedLearnerProfile | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const profile = cached?.owner === owner ? cached.profile : null;

  const refresh = useCallback(async () => {
    if (!session || !enabled || !owner) return;
    setLoading(true);
    setError(null);
    try {
      setCached({ owner, profile: await getLearnerProfile(session) });
    } catch (nextError) {
      setError(message(nextError));
    } finally {
      setLoading(false);
    }
  }, [enabled, owner, session]);

  useEffect(() => {
    if (!owner) setCached(null);
  }, [owner]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      setError(null);
      return;
    }
    if (profile) return;
    void refresh();
  }, [enabled, profile, refresh]);

  async function mutate(action: () => Promise<unknown>) {
    if (!session || !owner) return;
    setLoading(true);
    setError(null);
    try {
      const result = await action();
      setCached({
        owner,
        profile: result ? (result as LearnerProfile) : await getLearnerProfile(session),
      });
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
