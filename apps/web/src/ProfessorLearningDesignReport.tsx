import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import type { LearningDesignDiagnostic, LearningDesignReport } from "./learningDesignTypes";

export function ProfessorLearningDesignReport({
  acknowledgementResetKey,
  approved,
  dirty,
  lectureId,
  report,
  saving,
  onApprove,
}: {
  acknowledgementResetKey: string;
  approved: boolean;
  dirty: boolean;
  lectureId: string;
  report: LearningDesignReport;
  saving: boolean;
  onApprove: (lectureId: string, acknowledgedWarningIds: string[]) => void;
}) {
  const { t } = useI18n();
  const [acknowledged, setAcknowledged] = useState<string[]>([]);
  useEffect(() => setAcknowledged([]), [acknowledgementResetKey, report.report_revision]);
  const warningIds = report.diagnostics.map((diagnostic) => diagnostic.id);
  const allAcknowledged = warningIds.every((id) => acknowledged.includes(id));
  return (
    <section className="learning-design-report">
      <h4>{t("builder.learningDesign.reportTitle")}</h4>
      <div className="learning-design-coverage">
        <CoverageRow
          label={t("builder.learningDesign.gateCoverage")}
          coverage={report.coverage.gate_concepts}
          unit={t("builder.learningDesign.conceptsUnit")}
        />
        <CoverageRow
          label={t("builder.learningDesign.quizCoverage")}
          coverage={report.coverage.quiz_concepts}
          unit={t("builder.learningDesign.conceptsUnit")}
        />
        <CoverageRow
          label={t("builder.learningDesign.sourceCoverage")}
          coverage={report.coverage.source_backed_assessments}
          unit={t("builder.learningDesign.assessmentsUnit")}
        />
        <CoverageRow
          label={t("builder.learningDesign.transferCoverage")}
          coverage={report.coverage.transfer_prompts}
          unit={t("builder.learningDesign.gatesUnit")}
        />
      </div>
      {report.diagnostics.length ? (
        <ul className="learning-design-diagnostics">
          {report.diagnostics.map((diagnostic) => (
            <li key={diagnostic.id}>
              <label>
                <input
                  checked={acknowledged.includes(diagnostic.id)}
                  type="checkbox"
                  onChange={(event) =>
                    setAcknowledged((current) =>
                      event.target.checked
                        ? [...current, diagnostic.id]
                        : current.filter((id) => id !== diagnostic.id),
                    )
                  }
                />
                <span>
                  <strong>{diagnostic.message}</strong>
                  <span>{diagnostic.action}</span>
                  <small>{coordinatesLabel(diagnostic, t)}</small>
                </span>
              </label>
            </li>
          ))}
        </ul>
      ) : (
        <p>{t("builder.learningDesign.noWarnings")}</p>
      )}
      {allAcknowledged && report.diagnostics.length ? (
        <p role="status">{t("builder.learningDesign.acknowledgedExactDraft")}</p>
      ) : null}
      <button
        disabled={dirty || saving || approved || !allAcknowledged}
        type="button"
        onClick={() => onApprove(lectureId, warningIds)}
      >
        {approved ? t("builder.learningDesign.approved") : t("builder.learningDesign.approve")}
      </button>
    </section>
  );
}

function CoverageRow({
  coverage,
  label,
  unit,
}: {
  coverage: LearningDesignReport["coverage"][keyof LearningDesignReport["coverage"]];
  label: string;
  unit: string;
}) {
  const { t } = useI18n();
  const value =
    coverage.status === "not_applicable"
      ? t("builder.learningDesign.notApplicable")
      : `${coverage.covered}/${coverage.total} ${unit}`;
  return <p>{`${label}: ${value}`}</p>;
}

function coordinatesLabel(
  diagnostic: LearningDesignDiagnostic,
  t: ReturnType<typeof useI18n>["t"],
) {
  const coordinates = diagnostic.coordinates;
  return [
    coordinates.section_id
      ? `${t("builder.learningDesign.sectionCoordinate")} ${coordinates.section_id}`
      : null,
    coordinates.assessment_id
      ? `${t("builder.learningDesign.assessmentCoordinate")} ${coordinates.assessment_id}`
      : null,
    coordinates.block_id
      ? `${t("builder.learningDesign.blockCoordinate")} ${coordinates.block_id}`
      : null,
    coordinates.prerequisite_section_id
      ? `${t("builder.learningDesign.prerequisiteCoordinate")} ${coordinates.prerequisite_section_id}`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");
}
