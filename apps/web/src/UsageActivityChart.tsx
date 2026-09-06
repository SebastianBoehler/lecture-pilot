import { useId, useState } from "react";
import { useI18n } from "./i18n";
import { usageHistory } from "./usageHistoryData";
import type { ProfessorUsageSummary } from "./usageTypes";

type Metric = "model_requests" | "tutor_turns" | "total_tokens";
export function UsageActivityChart({ usage }: { usage: ProfessorUsageSummary }) {
  const { locale, t } = useI18n();
  const id = useId();
  const [metric, setMetric] = useState<Metric>("model_requests");
  const days = usageHistory(usage);
  const max = Math.max(1, ...days.map((day) => day[metric]));
  const labels = {
    model_requests: t("usage.modelRequests"),
    tutor_turns: t("dashboard.tutorRequests"),
    total_tokens: t("usage.totalTokens"),
  };
  const format = (value: number) => new Intl.NumberFormat(locale).format(value);
  const dateLabel = (date: string) =>
    new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", timeZone: "UTC" }).format(
      new Date(`${date}T00:00:00Z`),
    );
  const step = 600 / Math.max(1, days.length);
  return (
    <section className="usage-section usage-history">
      <header className="dashboard-section-header">
        <h2>{t("dashboard.dailyActivity")}</h2>
        <label>
          {t("dashboard.metric")}
          <select value={metric} onChange={(event) => setMetric(event.target.value as Metric)}>
            {Object.entries(labels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </header>
      <p className="dashboard-hint">
        {dateLabel(usage.period_start)} – {dateLabel(usage.period_end)} ·{" "}
        {t("dashboard.recordedDays")}
      </p>
      <svg viewBox="0 0 680 210" role="img" aria-labelledby={id}>
        <title id={id}>
          {labels[metric]} · {usage.period_start} – {usage.period_end}
        </title>
        {[0, 0.5, 1].map((fraction) => (
          <g key={fraction}>
            <line
              x1="60"
              x2="660"
              y1={170 - fraction * 140}
              y2={170 - fraction * 140}
              className="usage-chart-grid"
            />
            <text x="52" y={174 - fraction * 140} textAnchor="end">
              {new Intl.NumberFormat(locale, {
                notation: "compact",
                maximumFractionDigits: 1,
              }).format(max * fraction)}
            </text>
          </g>
        ))}
        {days.map((day, index) => (
          <rect
            key={day.date}
            x={60 + index * step + step * 0.12}
            y={170 - (day[metric] / max) * 140}
            width={step * 0.76}
            height={(day[metric] / max) * 140}
            className="usage-chart-bar"
          >
            <title>
              {dateLabel(day.date)}: {format(day[metric])} {labels[metric]}
            </title>
          </rect>
        ))}
        <text x="60" y="197">
          {dateLabel(usage.period_start)}
        </text>
        <text x="660" y="197" textAnchor="end">
          {dateLabel(usage.period_end)}
        </text>
      </svg>
      <details className="dashboard-details">
        <summary>{t("dashboard.dailyValues")}</summary>
        <div className="usage-history-table">
          <table>
            <caption>{labels[metric]}</caption>
            <thead>
              <tr>
                <th>{t("dashboard.date")}</th>
                <th>{labels[metric]}</th>
              </tr>
            </thead>
            <tbody>
              {days.map((day) => (
                <tr key={day.date}>
                  <th scope="row">{day.date}</th>
                  <td>{format(day[metric])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
