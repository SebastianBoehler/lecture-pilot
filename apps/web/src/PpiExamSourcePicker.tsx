import { useState } from "react";

import { useI18n } from "./i18n";
import { importPpiExamSource, loadPpiCatalog } from "./practiceExamApi";
import type { PpiCatalog, PpiCredentials, PpiExamSource } from "./practiceExamTypes";
import type { LoginSession } from "./types";

export function PpiExamSourcePicker({
  courseId,
  session,
  onImported,
  onImportingChange,
}: {
  courseId: string;
  session: LoginSession;
  onImported: (source: PpiExamSource) => void;
  onImportingChange: (importing: boolean) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [credentials, setCredentials] = useState<PpiCredentials>({ username: "", password: "" });
  const [catalog, setCatalog] = useState<PpiCatalog | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<number | "catalog" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const normalizedQuery = normalizeSearchValue(query.trim());
  const visibleLectures =
    catalog?.lectures.filter((lecture) =>
      normalizeSearchValue(lecture.title).includes(normalizedQuery),
    ) ?? [];
  const importingLecture =
    typeof busy === "number"
      ? (catalog?.lectures.find((lecture) => lecture.id === busy) ?? null)
      : null;

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
    onImportingChange(true);
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
      onImportingChange(false);
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}>
        {t("practice.ppi.import")}
      </button>
    );
  }

  if (importingLecture) {
    return (
      <div aria-busy="true" aria-live="polite" className="practice-ppi-import-progress">
        <span aria-hidden="true" className="practice-button-spinner" />
        <div>
          <strong>{t("practice.ppi.importing")}</strong>
          <span>
            {importingLecture.title} ·{" "}
            {t("practice.ppi.protocolCount", { count: importingLecture.protocol_count })}
          </span>
        </div>
        <p>{t("practice.ppi.importingHelp")}</p>
      </div>
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
            name="ppi-username"
            spellCheck={false}
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
            name="ppi-password"
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
          <div className="practice-ppi-catalog-tools">
            <label className="practice-ppi-search">
              <span>{t("practice.ppi.searchLabel")}</span>
              <input
                autoComplete="off"
                placeholder={t("practice.ppi.searchPlaceholder")}
                spellCheck={false}
                type="search"
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
            </label>
            <p className="practice-ppi-token-balance">
              {t("practice.ppi.tokens", { count: catalog.tokens })}
            </p>
          </div>
          <p aria-live="polite" className="practice-ppi-result-count" role="status">
            {t("practice.ppi.resultCount", {
              count: visibleLectures.length,
              total: catalog.lectures.length,
            })}
          </p>
          {visibleLectures.length ? (
            <ul aria-label={t("practice.ppi.resultsLabel")} className="practice-ppi-catalog-list">
              {visibleLectures.map((lecture) => {
                const needsToken = !lecture.download_available && !lecture.borrowed;
                const importing = busy === lecture.id;
                return (
                  <li className="practice-ppi-course" key={lecture.id}>
                    <div className="practice-ppi-course-details">
                      <strong>{lecture.title}</strong>
                      <span>
                        {t("practice.ppi.protocolCount", { count: lecture.protocol_count })}
                      </span>
                    </div>
                    <div className="practice-ppi-course-action">
                      {lecture.cached_source_id ? (
                        <span className="practice-ppi-saved-badge">
                          {t("practice.ppi.savedBadge")}
                        </span>
                      ) : needsToken ? (
                        <button
                          aria-label={
                            importing
                              ? t("practice.ppi.importingCourse", { course: lecture.title })
                              : t("practice.ppi.borrowCourse", { course: lecture.title })
                          }
                          disabled={busy !== null || !lecture.can_borrow}
                          type="button"
                          onClick={() => void importLecture(lecture.id, true)}
                        >
                          {importing
                            ? t("practice.ppi.importing")
                            : t("practice.ppi.borrowForToken")}
                        </button>
                      ) : (
                        <button
                          aria-label={
                            importing
                              ? t("practice.ppi.importingCourse", { course: lecture.title })
                              : t("practice.ppi.importCourse", { course: lecture.title })
                          }
                          disabled={busy !== null}
                          type="button"
                          onClick={() => void importLecture(lecture.id, false)}
                        >
                          {importing
                            ? t("practice.ppi.importing")
                            : t("practice.ppi.importBorrowed")}
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="practice-ppi-no-results">
              <p>
                {query.trim()
                  ? t("practice.ppi.noMatches", { query: query.trim() })
                  : t("practice.ppi.noCourses")}
              </p>
              {query.trim() ? (
                <button type="button" onClick={() => setQuery("")}>
                  {t("practice.ppi.clearSearch")}
                </button>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function normalizeSearchValue(value: string) {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase();
}
