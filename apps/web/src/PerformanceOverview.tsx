import type { ReactNode } from "react";
import { CheckCircle2, Users } from "lucide-react";

import { useI18n } from "./i18n";
import type { LectureSnapshot } from "./performanceMetrics";

export function PerformanceOverview({
  label,
  snapshot,
}: {
  label?: string;
  snapshot: LectureSnapshot;
}) {
  const { t } = useI18n();
  return (
    <div className="performance-overview" aria-label={label ?? t("analytics.selectedOverview")}>
      <MetricCard
        icon={<Users size={18} />}
        label={t("analytics.activeLearners")}
        value={String(snapshot.learners)}
      />
      <MetricCard
        icon={<CheckCircle2 size={18} />}
        label={t("analytics.quizFirstAttempt")}
        value={snapshot.quizRate}
        detail={evidenceDetail(snapshot.quizEvidence, t("analytics.quizFirstAttempt"), t)}
      />
      <MetricCard
        icon={<CheckCircle2 size={18} />}
        label={t("analytics.independentFirstPass")}
        value={snapshot.gateRate}
        detail={evidenceDetail(snapshot.gateEvidence, t("analytics.independentFirstPass"), t)}
      />
      {snapshot.publicationVersion !== null ? (
        <details className="analytics-version-context dashboard-details">
          <summary>{t("dashboard.dataDetails")}</summary>
          <span>{t("analytics.activityEvents", { count: snapshot.events })}</span>
          <span>{t("analytics.publicationCurrent", { version: snapshot.publicationVersion })}</span>
          <span>
            {t("analytics.learningMapRevision", { revision: snapshot.learningMapRevision ?? "—" })}
          </span>
        </details>
      ) : null}
    </div>
  );
}

function MetricCard({
  detail,
  icon,
  label,
  value,
}: {
  detail?: string | null;
  icon?: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="analytics-kpi">
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function evidenceDetail(
  cell: LectureSnapshot["quizEvidence"],
  evidence: string,
  t: ReturnType<typeof useI18n>["t"],
) {
  if (!cell) return null;
  const status = t(
    cell.data_status === "available"
      ? "analytics.dataStatus.available"
      : "analytics.dataStatus.insufficient",
  );
  return t("analytics.evidenceDenominator", {
    count: cell.sample_size,
    evidence,
    status,
  });
}
