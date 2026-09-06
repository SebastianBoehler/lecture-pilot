import { useState } from "react";
import { useI18n } from "./i18n";
import {
  listPracticeAttempts,
  deletePracticeAttempt,
  type PracticeAttempt,
} from "./practiceAttemptApi";
import type { LoginSession } from "./types";

export function PracticeAttemptHistory({
  courseId,
  examId,
  session,
  onReview,
  disabled,
  onDelete,
}: {
  courseId: string;
  examId: string;
  session: LoginSession;
  onReview: (attempt: PracticeAttempt) => void;
  disabled: boolean;
  onDelete: (id: string) => void;
}) {
  const { t } = useI18n();
  const [records, setRecords] = useState<PracticeAttempt[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function load(deleteId?: string) {
    setBusy(true);
    setError(null);
    try {
      if (deleteId) {
        await deletePracticeAttempt(courseId, examId, session, deleteId);
        onDelete(deleteId);
      }
      setRecords(await listPracticeAttempts(courseId, examId, session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.history.failed"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="practice-attempt-history" aria-label={t("practice.history.title")}>
      <button
        type="button"
        disabled={busy || disabled}
        aria-expanded={records !== null}
        onClick={() => (records ? setRecords(null) : void load())}
      >
        {busy ? t("practice.history.loading") : t("practice.history.title")}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {records ? (
        <>
          <p>{t("practice.history.explanation")}</p>
          {records.length ? (
            <ul>
              {records.map((record) => (
                <li key={record.id}>
                  <time dateTime={record.created_at}>
                    {new Date(record.created_at).toLocaleString()}
                  </time>
                  <button
                    type="button"
                    disabled={busy || disabled}
                    onClick={() => onReview(record)}
                  >
                    {t("practice.history.review")}
                  </button>
                  <button
                    type="button"
                    disabled={busy || disabled}
                    onClick={() => void load(record.id)}
                  >
                    {t("practice.history.delete")}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("practice.history.empty")}</p>
          )}
        </>
      ) : null}
    </section>
  );
}
