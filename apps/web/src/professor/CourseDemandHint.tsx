import { useEffect, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { apiRequest } from "../shared/apiRequest";
import type { LoginSession } from "../shared/types";

const DEBOUNCE_MS = 400;

type CourseDemandMatch = { request_count: number; enrolled_user_count: number };

/** Tells a course builder how many students already asked for a course with this title and term. */
export function CourseDemandHint({
  session,
  term,
  title,
}: {
  session: LoginSession;
  term: string;
  title: string;
}) {
  const { t } = useI18n();
  const query = title.trim();
  const [match, setMatch] = useState<{ key: string; requests: number } | null>(null);
  const key = `${query}\u0000${term}`;

  useEffect(() => {
    if (query.length < 3) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ title: query });
      if (term.trim()) params.set("term", term.trim());
      apiRequest(
        session,
        `/admin/course-support-demand/match?${params}`,
        "Course demand could not be loaded.",
        { signal: controller.signal },
      )
        .then((payload) => {
          if (isMatch(payload)) setMatch({ key, requests: payload.request_count });
        })
        // The hint is advisory; course creation continues without it.
        .catch(() => undefined);
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key, query, session, term]);

  const requests = match?.key === key && query.length >= 3 ? match.requests : 0;
  if (requests < 1) return null;
  return (
    <p className="course-demand-hint" role="status">
      {requests === 1
        ? t("courseSupport.builderHintOne")
        : t("courseSupport.builderHint", { count: requests })}
    </p>
  );
}

function isMatch(value: unknown): value is CourseDemandMatch {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as CourseDemandMatch).request_count === "number" &&
    typeof (value as CourseDemandMatch).enrolled_user_count === "number"
  );
}
