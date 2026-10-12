import { useEffect, useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";

import { getCourseDemand, type CourseDemandRow } from "./courseDemandApi";
import { useI18n } from "../i18n/i18n";
import type { LoginSession } from "../shared/types";

export function CourseDemandPage({ session }: { session: LoginSession }) {
  const { t } = useI18n();
  const [rows, setRows] = useState<CourseDemandRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void getCourseDemand(session)
      .then((items) => active && setRows(items))
      .catch((reason: unknown) => {
        if (active)
          setError(reason instanceof Error ? reason.message : t("courseDemand.loadFailed"));
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [reload, session, t]);

  return (
    <main className="professor-screen course-demand-page">
      <section className="professor-page-header course-demand-header">
        <div>
          <h1>{t("courseDemand.title")}</h1>
          <p>{t("courseDemand.subtitle")}</p>
        </div>
        <button
          aria-label={t("courseDemand.refresh")}
          className="refresh-button"
          disabled={loading}
          type="button"
          onClick={() => setReload((current) => current + 1)}
        >
          <RefreshCw className={loading ? "is-spinning" : ""} size={15} />
        </button>
      </section>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {rows === null ? (
        !error ? (
          <p className="course-demand-status" role="status">
            {t("courseDemand.loading")}
          </p>
        ) : null
      ) : rows.length ? (
        <CourseDemandTable rows={rows} />
      ) : (
        <p className="course-demand-status">{t("courseDemand.empty")}</p>
      )}
    </main>
  );
}

function CourseDemandTable({ rows }: { rows: CourseDemandRow[] }) {
  const { locale, t } = useI18n();
  const date = (value: string | null) =>
    value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value)) : "–";
  return (
    <div className="course-demand-table-wrap">
      <table className="course-demand-table">
        <thead>
          <tr>
            <th scope="col">{t("courseDemand.course")}</th>
            <th scope="col">{t("courseDemand.instructor")}</th>
            <th scope="col">{t("courseDemand.requests")}</th>
            <th scope="col">{t("courseDemand.enrolled")}</th>
            <th scope="col">{t("courseDemand.firstRequest")}</th>
            <th scope="col">{t("courseDemand.lastRequest")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const source = row.source === "alma" ? "Alma" : "ILIAS";
            const link = externalUrl(row.display_url);
            return (
              <tr key={`${row.source}:${row.external_course_id}:${row.term}`}>
                <th scope="row">
                  <div className="course-demand-course">
                    <span className="course-demand-title">{row.title}</span>
                    <span className="course-demand-meta">
                      {[row.number, row.term, row.organization, source].filter(Boolean).join(" · ")}
                    </span>
                    {row.has_workspace ? (
                      <span className="course-demand-tag">{t("courseDemand.linked")}</span>
                    ) : null}
                    {link ? (
                      <a
                        className="course-demand-link"
                        href={link}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        {t("courseDemand.openSource", { source })}
                        <ExternalLink aria-hidden="true" size={12} />
                      </a>
                    ) : null}
                  </div>
                </th>
                <td>{row.instructor ?? "–"}</td>
                <td className="course-demand-number">{row.request_count}</td>
                <td className="course-demand-number">{row.enrolled_user_count}</td>
                <td>{date(row.first_requested_at)}</td>
                <td>{date(row.last_requested_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function externalUrl(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}
