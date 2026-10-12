import { useEffect, useState } from "react";

import {
  courseSupportKeyId,
  getCourseSupportRequests,
  setCourseSupportRequest,
  type CourseSupportKey,
  type CourseSupportStatus,
} from "./courseSupportApi";
import type { LoginSession } from "../shared/types";

export type CourseSupportRequestsState = {
  /** Null until loaded, or when the backend cannot serve requests for this account. */
  statuses: ReadonlyMap<string, CourseSupportStatus> | null;
  pendingKey: string | null;
  failedKey: string | null;
  toggle: (key: CourseSupportKey, requested: boolean) => Promise<void>;
};

export function useCourseSupportRequests(
  session: LoginSession | null,
  enabled: boolean,
): CourseSupportRequestsState {
  const [statuses, setStatuses] = useState<ReadonlyMap<string, CourseSupportStatus> | null>(null);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [failedKey, setFailedKey] = useState<string | null>(null);

  useEffect(() => {
    if (!session || !enabled) return;
    let active = true;
    getCourseSupportRequests(session)
      .then((items) => {
        if (active) setStatuses(new Map(items.map((item) => [courseSupportKeyId(item), item])));
      })
      .catch(() => {
        // Requests are optional; the course list stays usable without them.
        if (active) setStatuses(null);
      });
    return () => {
      active = false;
    };
  }, [enabled, session]);

  async function toggle(key: CourseSupportKey, requested: boolean) {
    if (!session) return;
    const id = courseSupportKeyId(key);
    setPendingKey(id);
    setFailedKey(null);
    try {
      const status = await setCourseSupportRequest(session, key, requested);
      setStatuses((current) => new Map(current ?? []).set(id, status));
    } catch {
      setFailedKey(id);
    } finally {
      setPendingKey(null);
    }
  }

  return { statuses, pendingKey, failedKey, toggle };
}
