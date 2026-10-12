import { useState } from "react";
import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import { useI18n } from "./i18n";
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
  const { t } = useI18n();
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
      if (!response.ok) throw new Error(readApiError(payload, t("review.changes.failed")));
      setReport(payload.report);
      setLoaded(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("review.changes.failed"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="implementation-changes">
      <summary>{t("review.changes.title")}</summary>
      <button type="button" disabled={busy} onClick={() => void load()}>
        {busy ? t("review.changes.loading") : t("review.changes.load")}
      </button>
      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}
      {loaded && !report ? <p>{t("review.changes.none")}</p> : null}
      {loaded && report ? (
        <>
          {report.reason ? (
            <p>
              <strong>{t("review.changes.reason")}</strong> {report.reason}
            </p>
          ) : (
            <p>{t("review.changes.noReason")}</p>
          )}
          <p>{t("review.changes.help")}</p>
          {report.changes.map((change) => (
            <details key={`${change.target_id}:${change.field}`}>
              <summary>
                {change.target_title} · {change.field.replaceAll("_", " ")}
              </summary>
              <div className="language-comparison">
                <div>
                  <strong>{t("review.changes.before")}</strong>
                  <pre>{display(change.before, t("review.changes.unset"))}</pre>
                </div>
                <div>
                  <strong>{t("review.changes.after")}</strong>
                  <pre>{display(change.after, t("review.changes.unset"))}</pre>
                </div>
              </div>
            </details>
          ))}
        </>
      ) : null}
    </details>
  );
}
function display(value: unknown, unset: string) {
  return value == null ? unset : typeof value === "string" ? value : JSON.stringify(value, null, 2);
}
