import type { ReactNode } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, Users } from "lucide-react";

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
        icon={<BarChart3 size={18} />}
        label={t("analytics.events")}
        value={String(snapshot.events)}
      />
      <MetricCard
        icon={<CheckCircle2 size={18} />}
        label={t("analytics.quizFirstAttempt")}
        value={snapshot.quizRate}
        detail={evidenceDetail(snapshot.quizEvidence, t("analytics.quizFirstAttempt"), t)}
      />
      <MetricCard
        icon={<Users size={18} />}
        label={t("analytics.activeLearners")}
        value={String(snapshot.learners)}
      />
      <MetricCard
        icon={<AlertTriangle size={18} />}
        label={t("analytics.independentFirstPass")}
        value={snapshot.gateRate}
        detail={evidenceDetail(snapshot.gateEvidence, t("analytics.independentFirstPass"), t)}
      />
      {snapshot.publicationVersion !== null ? (
        <div className="analytics-version-context">
          <span>{t("analytics.publicationCurrent", { version: snapshot.publicationVersion })}</span>
          <span>
            {t("analytics.learningMapRevision", { revision: snapshot.learningMapRevision ?? "—" })}
          </span>
        </div>
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
