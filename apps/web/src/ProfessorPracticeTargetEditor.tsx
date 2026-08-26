import { useId, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticeTargetEditorSection } from "./ProfessorPracticeTargetEditorSection";
import type { PracticeTarget } from "./practiceDesignTypes";

export type PracticeEditorSection =
  "outcome" | "sequence" | "evidence" | "misconceptions" | "hints" | "sources";

const EDITOR_SECTIONS: readonly PracticeEditorSection[] = [
  "outcome",
  "sequence",
  "evidence",
  "misconceptions",
  "hints",
  "sources",
];

export function ProfessorPracticeTargetEditor({
  disabled,
  target,
  onChange,
}: {
  disabled: boolean;
  target: PracticeTarget;
  onChange: (target: PracticeTarget) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<PracticeEditorSection>("outcome");
  const regionId = useId();
  const headingId = useId();
  return (
    <div className="practice-target-editor">
      <button
        aria-controls={regionId}
        aria-expanded={open}
        disabled={disabled}
        type="button"
        onClick={() => setOpen(!open)}
      >
        {open ? t("builder.design.finishEditingTarget") : t("builder.design.editTarget")}
      </button>
      {open ? (
        <section aria-labelledby={headingId} className="practice-target-editor-panel" id={regionId}>
          <header>
            <h4 id={headingId}>{t("builder.design.targetedEditTitle")}</h4>
            <p>{t("builder.design.targetedEditHelp")}</p>
          </header>
          <label className="practice-editor-section-picker">
            {t("builder.design.chooseEditSection")}
            <select
              disabled={disabled}
              value={section}
              onChange={(event) => setSection(event.target.value as PracticeEditorSection)}
            >
              {EDITOR_SECTIONS.map((value) => (
                <option key={value} value={value}>
                  {t(`builder.design.editSections.${value}`)}
                </option>
              ))}
            </select>
          </label>
          <details className="practice-technical-details">
            <summary>{t("builder.design.technicalDetails")}</summary>
            <dl>
              <dt>{t("builder.design.targetId")}</dt>
              <dd>
                <code>{target.id}</code>
              </dd>
            </dl>
          </details>
          <ProfessorPracticeTargetEditorSection
            disabled={disabled}
            section={section}
            target={target}
            onChange={onChange}
          />
        </section>
      ) : null}
    </div>
  );
}
