import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { getProfessorUsage } from "./usageApi";
import { useI18n } from "./i18n";
import type { LoginSession } from "./types";
import type { ProfessorUsageSummary, UsageActivity } from "./usageTypes";

const ranges = [7, 30, 90] as const;

export function ProfessorUsage({ session }: { session: LoginSession }) {
  const { locale, t } = useI18n();
  const [days, setDays] = useState(30);
  const [usage, setUsage] = useState<ProfessorUsageSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void getProfessorUsage(session, days)
      .then((result) => active && setUsage(result))
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : t("usage.loadFailed"));
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [days, reload, session, t]);

  return (
    <main className="professor-screen usage-page">
      <section className="professor-page-header usage-header">
        <div>
          <h1>{t("usage.title")}</h1>
          <p>{t("usage.subtitle")}</p>
        </div>
        <div className="usage-actions">
          <div className="usage-range" aria-label={t("usage.period")}>
            {ranges.map((range) => (
              <button
                className={days === range ? "is-active" : ""}
                key={range}
                type="button"
                onClick={() => setDays(range)}
              >
                {t("usage.days", { count: range })}
              </button>
            ))}
          </div>
          <button
            aria-label={t("usage.refresh")}
            className="refresh-button"
            disabled={loading}
            type="button"
            onClick={() => setReload((current) => current + 1)}
          >
            <RefreshCw className={loading ? "is-spinning" : ""} size={15} />
          </button>
        </div>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {usage ? (
        <>
          <UsageOverview usage={usage} locale={locale} />
          <div className="usage-columns">
            <UsageTable
              label={t("usage.byFunction")}
              rows={usage.workloads.map((item) => ({
                key: item.workload,
                label: workloadLabel(item.workload, t),
                activity: { ...item, tutor_turns: 0, images: 0 },
              }))}
              locale={locale}
            />
            <UsageTable
              label={t("usage.byCourse")}
              rows={usage.courses.map((item) => ({
                key: item.course_id,
                label: item.course_title,
                activity: item,
              }))}
              locale={locale}
            />
          </div>
          <UsageTimeline usage={usage} locale={locale} />
          <UsageLimits usage={usage} locale={locale} />
        </>
      ) : !error ? (
        <p className="usage-loading" role="status">
          {t("usage.loading")}
        </p>
      ) : null}
    </main>
  );
}

function UsageOverview({ usage, locale }: { usage: ProfessorUsageSummary; locale: string }) {
  const { t } = useI18n();
  const values = [
    [t("usage.modelRequests"), usage.totals.model_requests],
    [t("usage.totalTokens"), usage.totals.total_tokens],
    [t("usage.inputTokens"), usage.totals.input_tokens],
    [t("usage.outputTokens"), usage.totals.output_tokens],
  ] as const;
  return (
    <section className="usage-overview" aria-label={t("usage.overview")}>
      {values.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{number(value, locale)}</strong>
        </div>
      ))}
      <p>
        {t("usage.tokenDetails", {
          cached: number(usage.totals.cached_input_tokens, locale),
          reasoning: number(usage.totals.reasoning_tokens, locale),
        })}
      </p>
      <p>
        {t("usage.tutorDetails", {
          turns: number(usage.totals.tutor_turns, locale),
          images: number(usage.totals.images, locale),
        })}
      </p>
      <small>{t("usage.recordingNotice")}</small>
    </section>
  );
}

function UsageTable({ rows, label, locale }: { rows: UsageRow[]; label: string; locale: string }) {
  const { t } = useI18n();
  return (
    <section className="usage-section">
      <h2>{label}</h2>
      {rows.length ? (
        <div className="usage-table" role="table" aria-label={label}>
          {rows.map((row) => (
            <div className="usage-table-row" role="row" key={row.key}>
              <strong role="cell">{row.label}</strong>
              <span role="cell">
                {t("usage.requestsShort", { count: number(row.activity.model_requests, locale) })}
              </span>
              <span role="cell">
                {t("usage.tokensShort", { count: number(row.activity.total_tokens, locale) })}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="usage-empty">{t("usage.noRecordedUsage")}</p>
      )}
    </section>
  );
}

function UsageTimeline({ usage, locale }: { usage: ProfessorUsageSummary; locale: string }) {
  const { t } = useI18n();
  const max = Math.max(1, ...usage.daily.map((item) => item.total_tokens));
  return (
    <section className="usage-section">
      <h2>{t("usage.activity")}</h2>
      {usage.daily.length ? (
        <div className="usage-timeline">
          {usage.daily.slice(-14).map((day) => (
            <div className="usage-day" key={day.date}>
              <time dateTime={day.date}>
                {new Intl.DateTimeFormat(locale).format(new Date(`${day.date}T12:00:00`))}
              </time>
              <div>
                <span style={{ width: `${Math.max(2, (day.total_tokens / max) * 100)}%` }} />
              </div>
              <strong>{number(day.total_tokens, locale)}</strong>
            </div>
          ))}
        </div>
      ) : (
        <p className="usage-empty">{t("usage.noRecordedUsage")}</p>
      )}
    </section>
  );
}

function UsageLimits({ usage, locale }: { usage: ProfessorUsageSummary; locale: string }) {
  const { t } = useI18n();
  return (
    <section className="usage-limits">
      <div>
        <h2>{t("usage.guardrails")}</h2>
        <p>{t("usage.guardrailsHelp")}</p>
      </div>
      <dl>
        <div>
          <dt>{t("usage.turnsPerDay")}</dt>
          <dd>{number(usage.limits.turns_per_day, locale)}</dd>
        </div>
        <div>
          <dt>{t("usage.reservedTokensPerDay")}</dt>
          <dd>{number(usage.limits.reserved_tokens_per_day, locale)}</dd>
        </div>
        <div>
          <dt>{t("usage.imagesPerDay")}</dt>
          <dd>{number(usage.limits.images_per_day, locale)}</dd>
        </div>
      </dl>
    </section>
  );
}

type UsageRow = { key: string; label: string; activity: UsageActivity };

function workloadLabel(workload: string, t: ReturnType<typeof useI18n>["t"]) {
  if (workload === "tutor") return t("usage.workloadTutor");
  if (workload === "course_schedule") return t("usage.workloadSchedule");
  if (workload === "course_canvas") return t("usage.workloadCanvas");
  return workload;
}

function number(value: number, locale: string) {
  return new Intl.NumberFormat(locale).format(value);
}
