import { useEffect, useId, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import { PerformanceInsights } from "./PerformanceInsights";
import { ProfessorLearningMapTree } from "./ProfessorLearningMapTree";
import type { LectureAnalyticsSummary } from "./types";

type AnalysisView = "quizzes" | "path" | "gates";

export function PerformanceAnalysisWorkspace({
  analytics,
}: {
  analytics: LectureAnalyticsSummary;
}) {
  const { t } = useI18n();
  const tabsId = useId();
  const counts = useMemo(
    () => ({
      gates: analytics.gates.length,
      path: analytics.learning_map?.nodes.length ?? 0,
      quizzes: analytics.quizzes.length,
    }),
    [analytics],
  );
  const preferredView = preferredAnalysisView(counts);
  const [activeView, setActiveView] = useState<AnalysisView>(preferredView);

  useEffect(() => setActiveView(preferredView), [analytics.lecture_id, preferredView]);

  const tabs: Array<{ count: number; label: string; view: AnalysisView }> = [
    { count: counts.quizzes, label: t("analytics.quizFriction"), view: "quizzes" },
    { count: counts.path, label: t("analytics.learningPathGates"), view: "path" },
    { count: counts.gates, label: t("analytics.gateEvidence"), view: "gates" },
  ];

  return (
    <section className="performance-analysis">
      <header className="performance-analysis-header">
        <div>
          <h3>{t("analytics.lectureEvidence")}</h3>
          <p>{t("analytics.lectureEvidenceHelp")}</p>
        </div>
        <div
          aria-label={t("analytics.lectureEvidence")}
          className="performance-analysis-tabs"
          role="tablist"
        >
          {tabs.map((tab) => (
            <button
              aria-controls={`${tabsId}-panel`}
              aria-selected={activeView === tab.view}
              disabled={!tab.count}
              id={`${tabsId}-${tab.view}`}
              key={tab.view}
              role="tab"
              type="button"
              onClick={() => setActiveView(tab.view)}
            >
              <span>{tab.label}</span>
              <strong>{tab.count}</strong>
            </button>
          ))}
        </div>
      </header>
      <div
        aria-labelledby={`${tabsId}-${activeView}`}
        className="performance-analysis-panel"
        id={`${tabsId}-panel`}
        role="tabpanel"
      >
        {activeView === "path" ? (
          <ProfessorLearningMapTree analytics={analytics} />
        ) : (
          <PerformanceInsights analytics={analytics} view={activeView} />
        )}
      </div>
    </section>
  );
}

function preferredAnalysisView(counts: Record<AnalysisView, number>): AnalysisView {
  if (counts.quizzes) return "quizzes";
  if (counts.path) return "path";
  return "gates";
}
