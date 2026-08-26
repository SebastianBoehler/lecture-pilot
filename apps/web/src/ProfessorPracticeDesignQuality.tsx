import { useId } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
import type { PracticeDesignQualityReview } from "./practiceDesignTypes";

export function ProfessorPracticeDesignQuality({
  dirty,
  qualityReview,
}: {
  dirty: boolean;
  qualityReview: PracticeDesignQualityReview | null;
}) {
  const { t } = useI18n();
  const headingId = useId();
  if (dirty)
    return (
      <section className="practice-quality is-required" aria-labelledby={headingId}>
        <h4 id={headingId}>{t("builder.design.changesNeedReview")}</h4>
        <p>{t("builder.design.changesNeedReviewHelp")}</p>
      </section>
    );
  if (!qualityReview)
    return (
      <section className="practice-quality is-required" aria-labelledby={headingId}>
        <h4 id={headingId}>{t("builder.design.reviewRequired")}</h4>
        <p>{t("builder.design.reviewRequiredHelp")}</p>
      </section>
    );

  const issues = qualityReview.checks.filter((check) => check.severity !== "pass");
  const critical = issues.filter((check) => check.severity === "critical").length;
  const warnings = issues.length - critical;
  return (
    <section className="practice-quality" aria-labelledby={headingId}>
      <header>
        <h4 id={headingId}>{t("builder.design.qualityReview")}</h4>
        <p>
          {t("builder.design.qualitySummary", {
            critical,
            warnings,
            passed: qualityReview.checks.length - issues.length,
          })}
        </p>
      </header>
      {issues.length ? (
        <ul className="practice-quality-findings">
          {issues.map((check) => (
            <li className={`is-${check.severity}`} key={check.dimension}>
              <div>
                <strong>{t(`builder.design.reviewSeverity.${check.severity}`)}</strong>
                <span>{t(`builder.design.reviewDimensions.${check.dimension}`)}</span>
              </div>
              <p>{check.summary}</p>
              {check.target_ids.length ? (
                <p>
                  {t("builder.design.affectedTargets", { targets: check.target_ids.join(", ") })}
                </p>
              ) : null}
              {check.supporting_anchors.map((anchor, index) => (
                <ProfessorPracticeEvidence anchor={anchor} key={`${anchor.source_path}-${index}`} />
              ))}
            </li>
          ))}
        </ul>
      ) : (
        <p className="practice-quality-passed">{t("builder.design.qualityPassed")}</p>
      )}
      <details className="practice-quality-all-checks">
        <summary>{t("builder.design.showAllChecks")}</summary>
        <ul>
          {qualityReview.checks.map((check) => (
            <li key={check.dimension}>
              <span>{t(`builder.design.reviewSeverity.${check.severity}`)}</span>
              <span>{t(`builder.design.reviewDimensions.${check.dimension}`)}</span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
