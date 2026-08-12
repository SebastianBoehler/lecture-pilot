import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import type { LearningDesignReport } from "./learningDesignTypes";

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
      <p>{t("builder.learningDesign.reportHelp")}</p>
      {report.diagnostics.length ? (
        <ul className="learning-design-diagnostics">
          {report.diagnostics.map((diagnostic) => (
            <li key={diagnostic.id}>
              <strong>{diagnostic.message}</strong>
              <span>{diagnostic.action}</span>
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
                {t("builder.learningDesign.acknowledgeFinding")}
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
