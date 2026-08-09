import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { getReviewQueue, openGateReview } from "./reviewQueueApi";
import type { CourseReviewQueue, GateReviewQueueItem } from "./reviewQueueTypes";
import type { LoginSession } from "./types";

type Snapshot = {
  key: string;
  data: CourseReviewQueue | null;
  loading: boolean;
  error: string | null;
};

export function useReviewQueue(courseId: string, session: LoginSession | null) {
  const enabled = Boolean(session?.roles?.includes("student") && courseId);
  const key =
    enabled && session ? JSON.stringify([session.tenant_id ?? "", session.username, courseId]) : "";
  const [snapshot, setSnapshot] = useState<Snapshot>({
    key: "",
    data: null,
    loading: false,
    error: null,
  });
  const activeKey = useRef(key);
  const versions = useRef(new Map<string, number>());

  useLayoutEffect(() => {
    activeKey.current = key;
  }, [key]);

  const refresh = useCallback(async () => {
    if (activeKey.current !== key) return;
    if (!key || !session) {
      setSnapshot({ key, data: null, loading: false, error: null });
      return;
    }
    const version = (versions.current.get(key) ?? 0) + 1;
    versions.current.set(key, version);
    setSnapshot((current) => ({
      key,
      data: current.key === key ? current.data : null,
      loading: true,
      error: null,
    }));
    try {
      const data = await getReviewQueue(courseId, session);
      if (activeKey.current === key && versions.current.get(key) === version) {
        setSnapshot({ key, data, loading: false, error: null });
      }
    } catch (error) {
      if (activeKey.current === key && versions.current.get(key) === version) {
        setSnapshot({
          key,
          data: null,
          loading: false,
          error: error instanceof Error ? error.message : "Review queue loading failed.",
        });
      }
    }
  }, [courseId, key, session]);

  useEffect(() => {
    const requestVersions = versions.current;
    void refresh();
    return () => {
      if (key) requestVersions.set(key, (requestVersions.get(key) ?? 0) + 1);
    };
  }, [key, refresh]);

  const open = useCallback(
    async (item: GateReviewQueueItem) => {
      if (!session || activeKey.current !== key) return null;
      try {
        const opening = await openGateReview(item, session);
        if (activeKey.current !== key) return null;
        await refresh();
        return activeKey.current === key ? opening : null;
      } catch (error) {
        if (activeKey.current === key) {
          setSnapshot((current) => ({
            ...current,
            error: error instanceof Error ? error.message : "Gate review opening failed.",
          }));
        }
        return null;
      }
    },
    [key, refresh, session],
  );

  return useMemo(
    () => ({
      queue: snapshot.key === key ? snapshot.data : null,
      loading: snapshot.key === key && snapshot.loading,
      error: snapshot.key === key ? snapshot.error : null,
      refresh,
      open,
    }),
    [key, open, refresh, snapshot],
  );
}
