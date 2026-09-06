import { useState } from "react";
import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

type Report = {
  reason: string | null;
  from_revision: string;
  to_revision: string;
  changes: Array<{
    target_id: string;
    target_title: string;
    field: string;
    before: unknown;
    after: unknown;
  }>;
};

export function ProfessorImplementationChanges({
  courseId,
  lectureId,
  session,
}: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
}) {
  const [report, setReport] = useState<Report | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function load() {
    setBusy(true);
    setError(null);
    setLoaded(false);
    try {
      const response = await fetch(
        apiUrl(
          `/admin/courses/${courseId}/lectures/${lectureId}/practice-design/implementation-changes`,
        ),
        authRequestInit(session),
      );
      const payload = await response.json();
      if (!response.ok)
        throw new Error(readApiError(payload, "Implementation changes could not be loaded."));
      setReport(payload.report);
      setLoaded(true);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Implementation changes could not be loaded.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="implementation-changes">
      <summary>Teaching implementation changes</summary>
      <button type="button" disabled={busy} onClick={() => void load()}>
        {busy ? "Loading changes…" : "Inspect current implementation changes"}
      </button>
      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}
      {loaded && !report ? (
        <p>No recorded implementation change is available for this revision.</p>
      ) : null}
      {loaded && report ? (
        <>
          {report.reason ? (
            <p>
              <strong>Recorded reason:</strong> {report.reason}
            </p>
          ) : (
            <p>No repair reason was recorded for this change.</p>
          )}
          <p>
            These are exact changes to teaching under the approved goals. Review their correctness
            against the sources.
          </p>
          {report.changes.map((change) => (
            <details key={`${change.target_id}:${change.field}`}>
              <summary>
                {change.target_title} · {change.field.replaceAll("_", " ")}
              </summary>
              <div className="language-comparison">
                <div>
                  <strong>Before</strong>
                  <pre>{display(change.before)}</pre>
                </div>
                <div>
                  <strong>After</strong>
                  <pre>{display(change.after)}</pre>
                </div>
              </div>
            </details>
          ))}
        </>
      ) : null}
    </details>
  );
}
function display(value: unknown) {
  return value == null
    ? "Not previously set"
    : typeof value === "string"
      ? value
      : JSON.stringify(value, null, 2);
}
