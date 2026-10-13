import type { ReactNode } from "react";

import { useI18n } from "../i18n/i18n";
import { formatLectureDate } from "../shared/lectureDate";
import type { LectureNextAction, LectureState } from "./courseLectureStateTypes";
import { CourseLectureStatusChip } from "./CourseLectureStatusChip";
import type { LecturePending } from "./useCourseLectureActions";

const PANEL_ACTIONS: readonly LectureNextAction[] = [
  "review_goals",
  "keep_or_regenerate_goals",
  "review_draft",
];

export function hasLecturePanel(action: LectureNextAction) {
  return PANEL_ACTIONS.includes(action);
}

/** One lecture: status, at most one primary next step, and its inline review panel. */
export function CourseLectureRow({
  lecture,
  open,
  pending,
  error,
  panel,
  onToggle,
  onConfirmRouting,
  onStartDraft,
  onPreview,
}: {
  lecture: LectureState;
  open: boolean;
  pending?: LecturePending;
  error?: string;
  panel: ReactNode;
  onToggle: () => void;
  onConfirmRouting: () => void;
  onStartDraft: () => void;
  onPreview?: () => void;
}) {
  const { locale, t } = useI18n();
  const panelId = `lecture-panel-${lecture.lecture_id}`;
  const failure = lecture.draft === "failed" ? lecture.draft_error : null;
  return (
    <>
      <tr className="course-lecture-row" data-open={open || undefined}>
        <td className="course-lecture-number">{lecture.number}</td>
        <th scope="row" className="course-lecture-title">
          <span>{lecture.title}</span>
          {lecture.sources === "new" && !lecture.published ? (
            <span className="course-lecture-new">{t("coursePage.new")}</span>
          ) : null}
          {failure ? (
            <span className="course-lecture-reason">
              {t("coursePage.draftFailed", { reason: failure })}
            </span>
          ) : null}
          {error ? (
            <span className="course-lecture-reason" role="alert">
              {error}
            </span>
          ) : null}
        </th>
        <td className="course-lecture-date">
          {lecture.date ? formatLectureDate(lecture.date, locale) : ""}
        </td>
        <td className="course-lecture-status">
          <CourseLectureStatusChip lecture={lecture} />
        </td>
        <td className="course-lecture-action">
          {onPreview && !hasLecturePanel(lecture.next_action) ? (
            <button
              className="course-quiet-button"
              type="button"
              aria-label={t("coursePage.previewLectureAria", { lecture: lecture.title })}
              onClick={onPreview}
            >
              {t("coursePage.previewLecture")}
            </button>
          ) : null}
          {primaryAction()}
        </td>
      </tr>
      {open && hasLecturePanel(lecture.next_action) ? (
        <tr className="course-lecture-panel-row">
          <td colSpan={5} id={panelId}>
            {panel}
          </td>
        </tr>
      ) : null}
    </>
  );

  function primaryAction() {
    const action = lecture.next_action;
    if (pending || action === "wait") {
      return (
        <button className="course-row-button" type="button" disabled aria-busy="true">
          <span className="course-spinner" aria-hidden="true" />
          {pending ? t(`coursePage.pending.${pending}`) : t("coursePage.action.wait")}
        </button>
      );
    }
    if (action === "none") return null;
    const label = t(`coursePage.action.${action}`);
    const panelAction = hasLecturePanel(action);
    return (
      <button
        className="course-row-button"
        data-primary={!panelAction || !open || undefined}
        type="button"
        aria-label={t("coursePage.actionFor", { action: label, lecture: lecture.title })}
        aria-expanded={panelAction ? open : undefined}
        aria-controls={panelAction && open ? panelId : undefined}
        onClick={
          panelAction ? onToggle : action === "confirm_routing" ? onConfirmRouting : onStartDraft
        }
      >
        {label}
      </button>
    );
  }
}
