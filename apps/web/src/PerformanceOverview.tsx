import type { ReactNode } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, Users } from "lucide-react";

import { useI18n } from "./i18n";
import type { LectureSnapshot } from "./performanceMetrics";

export function PerformanceOverview({ snapshot }: { snapshot: LectureSnapshot }) {
  const { t } = useI18n();
  return (
    <div className="performance-overview" aria-label={t("analytics.selectedOverview")}>
      <MetricCard
        icon={<BarChart3 size={18} />}
        label={t("analytics.events")}
        value={String(snapshot.events)}
      />
      <MetricCard
        icon={<CheckCircle2 size={18} />}
        label={t("analytics.quizSuccess")}
        value={snapshot.quizRate}
      />
      <MetricCard
        icon={<Users size={18} />}
        label={t("analytics.activeLearners")}
        value={String(snapshot.learners)}
      />
      <MetricCard
        icon={<AlertTriangle size={18} />}
        label={t("analytics.gatePassRate")}
        value={snapshot.gateRate}
      />
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon?: ReactNode; label: string; value: string }) {
  return (
    <div className="analytics-kpi">
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
    </div>
  );
}
