import { useI18n } from "../i18n/i18n";
import type { LectureState } from "./courseLectureStateTypes";
import { lectureStatus } from "./courseLectureStatus";

/** Status text carries the meaning; tone and glyph only reinforce it. */
export function CourseLectureStatusChip({ lecture }: { lecture: LectureState }) {
  const { t } = useI18n();
  const status = lectureStatus(lecture);
  return (
    <span className="course-status-chip" data-tone={status.tone} data-status={status.kind}>
      <span className="course-status-glyph" aria-hidden="true" />
      {t(`coursePage.status.${status.kind}`)}
    </span>
  );
}
