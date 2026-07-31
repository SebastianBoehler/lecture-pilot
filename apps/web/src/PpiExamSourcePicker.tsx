import { useState } from "react";

import { useI18n } from "./i18n";
import { importPpiExamSource, loadPpiCatalog } from "./practiceExamApi";
import type { PpiCatalog, PpiCredentials, PpiExamSource } from "./practiceExamTypes";
import type { LoginSession } from "./types";

export function PpiExamSourcePicker({
  courseId,
  session,
  onImported,
}: {
  courseId: string;
  session: LoginSession;
  onImported: (source: PpiExamSource) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [credentials, setCredentials] = useState<PpiCredentials>({ username: "", password: "" });
  const [catalog, setCatalog] = useState<PpiCatalog | null>(null);
  const [confirmed, setConfirmed] = useState<number[]>([]);
  const [busy, setBusy] = useState<number | "catalog" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadCatalog() {
    setBusy("catalog");
    setError(null);
    try {
      setCatalog(await loadPpiCatalog(courseId, credentials, session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.ppi.loadFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function importLecture(lectureId: number, spendToken: boolean) {
    setBusy(lectureId);
    setError(null);
    try {
      onImported(await importPpiExamSource(courseId, credentials, lectureId, spendToken, session));
      setCatalog(
        (current) =>
          current && {
            ...current,
            lectures: current.lectures.map((lecture) =>
              lecture.id === lectureId
                ? { ...lecture, cached_source_id: `ppi-${lectureId}` }
                : lecture,
            ),
          },
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.ppi.importFailed"));
    } finally {
      setBusy(null);
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}>
        {t("practice.ppi.import")}
      </button>
    );
  }

  return (
    <div className="practice-ppi-import">
      <h4>{t("practice.ppi.credentialsTitle")}</h4>
      <p>{t("practice.ppi.credentialsHelp")}</p>
      {error ? (
        <p className="practice-exam-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="practice-ppi-credentials">
        <label>
          <span>{t("practice.ppi.username")}</span>
          <input
            autoComplete="username"
            value={credentials.username}
            onChange={(event) =>
              setCredentials({ ...credentials, username: event.currentTarget.value })
            }
          />
        </label>
        <label>
          <span>{t("practice.ppi.password")}</span>
          <input
            autoComplete="current-password"
            type="password"
            value={credentials.password}
            onChange={(event) =>
              setCredentials({ ...credentials, password: event.currentTarget.value })
            }
          />
        </label>
        <button
          disabled={busy !== null || !credentials.username || !credentials.password}
          type="button"
          onClick={() => void loadCatalog()}
        >
          {busy === "catalog" ? t("practice.ppi.loading") : t("practice.ppi.load")}
        </button>
      </div>
      {catalog ? (
        <div className="practice-ppi-catalog">
          <p>{t("practice.ppi.tokens", { count: catalog.tokens })}</p>
          {catalog.lectures.map((lecture) => {
            const needsToken = !lecture.download_available && !lecture.borrowed;
            const tokenConfirmed = confirmed.includes(lecture.id);
            return (
              <article key={lecture.id}>
                <div>
                  <strong>{lecture.title}</strong>
                  <span>{t("practice.ppi.protocolCount", { count: lecture.protocol_count })}</span>
                </div>
                {lecture.cached_source_id ? (
                  <span>{t("practice.ppi.savedBadge")}</span>
                ) : needsToken ? (
                  <div className="practice-ppi-borrow">
                    <label>
                      <input
                        checked={tokenConfirmed}
                        type="checkbox"
                        onChange={() =>
                          setConfirmed((current) =>
                            tokenConfirmed
                              ? current.filter((id) => id !== lecture.id)
                              : [...current, lecture.id],
                          )
                        }
                      />
                      <span>{t("practice.ppi.confirmToken")}</span>
                    </label>
                    <button
                      disabled={!tokenConfirmed || busy !== null || !lecture.can_borrow}
                      type="button"
                      onClick={() => void importLecture(lecture.id, true)}
                    >
                      {t("practice.ppi.borrowImport")}
                    </button>
                  </div>
                ) : (
                  <button
                    disabled={busy !== null}
                    type="button"
                    onClick={() => void importLecture(lecture.id, false)}
                  >
                    {t("practice.ppi.importBorrowed")}
                  </button>
                )}
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
