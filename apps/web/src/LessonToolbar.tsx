import type { ReactNode } from "react";

import { useI18n } from "./i18n";
import { formatLectureDate } from "./lectureDate";
import type { Lecture } from "./types";
import { WorkspaceResetControl, type WorkspaceResetSelection } from "./WorkspaceResetControl";

export function LessonToolbar({
  lecture,
  languageControl,
  resetDisabled,
  onReset,
}: {
  lecture: Lecture;
  languageControl: ReactNode;
  resetDisabled: boolean;
  onReset: (options: WorkspaceResetSelection) => Promise<void>;
}) {
  const { locale, t } = useI18n();
  return (
    <div className="lesson-toolbar">
      <div className="lesson-toolbar-context">
        <p className="lesson-context">
          {t("lesson.context", {
            number: lecture.number,
            date: formatLectureDate(lecture.date, locale),
          })}
        </p>
        {languageControl}
      </div>
      <div className="lesson-toolbar-actions">
        <WorkspaceResetControl disabled={resetDisabled} onReset={onReset} />
      </div>
    </div>
  );
}
