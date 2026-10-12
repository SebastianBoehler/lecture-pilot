import { useId, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticePlanningContextEditor } from "./ProfessorPracticePlanningContext";
import type { PracticeDesign } from "./practiceDesignTypes";

export function ProfessorPracticeLectureEditor({
  draft,
  onChange,
}: {
  draft: PracticeDesign;
  onChange: (design: PracticeDesign) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const regionId = useId();
  return (
    <div className="practice-lecture-editor">
      <button
        aria-controls={regionId}
        aria-expanded={open}
        type="button"
        onClick={() => setOpen(!open)}
      >
        {open ? t("builder.design.finishEditing") : t("builder.design.editLecture")}
      </button>
      {open ? (
        <div className="practice-lecture-fields" id={regionId}>
          <label>
            {t("builder.design.lectureTitle")}
            <span>{t("builder.design.lectureTitleHelp")}</span>
            <textarea
              value={draft.lecture_title}
              onChange={(event) => onChange({ ...draft, lecture_title: event.target.value })}
            />
          </label>
          <p>{t("builder.intent.objectiveDerived")}</p>
          <ProfessorPracticePlanningContextEditor
            context={draft.planning_context}
            onChange={(planning_context) => onChange({ ...draft, planning_context })}
          />
        </div>
      ) : null}
    </div>
  );
}
