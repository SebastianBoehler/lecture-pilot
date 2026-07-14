import { X } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { CourseAccessFields } from "./CourseAccessFields";
import {
  datetimeLocalValue,
  editableAccessRule,
  formatAccessDate,
  formatRelativeAccess,
  lectureAvailability,
  publicationAtFromLocal,
} from "./courseAccessStatus";
import { useI18n } from "./i18n";
import type { CourseAccessRule, CourseAccessSaveInput } from "./courseAccessTypes";
import type { Lecture, ManagedCourseWorkspaceResult } from "./types";

export type ProfessorAccessTarget =
  | { kind: "course"; triggerId: string; workspace: ManagedCourseWorkspaceResult }
  | {
      kind: "lecture";
      lecture: Lecture;
      triggerId: string;
      workspace: ManagedCourseWorkspaceResult;
    };

export function ProfessorCourseAccessDialog({
  error,
  saving,
  target,
  onClose,
  onSave,
}: {
  error: string | null;
  saving: boolean;
  target: ProfessorAccessTarget;
  onClose: () => void;
  onSave: (input: CourseAccessSaveInput) => void;
}) {
  const { t } = useI18n();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const customErrorId = useId();
  const [rule, setRule] = useState(() => initialRule(target));
  const [inheritCourseDefault, setInheritCourseDefault] = useState(() => isInherited(target));
  const [confirmUniversityMembers, setConfirmUniversityMembers] = useState(false);
  const lecture = target.kind === "lecture" ? target.lecture : target.workspace.lectures[0];
  const customInvalid = rule.publication_mode === "custom" && !rule.publication_at;
  const needsUniversityConfirmation =
    !inheritCourseDefault && rule.audience === "platform_authenticated";

  useEffect(() => {
    setRule(initialRule(target));
    setInheritCourseDefault(isInherited(target));
    setConfirmUniversityMembers(false);
  }, [target]);

  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    return () => {
      if (typeof dialog.close === "function" && dialog.open) dialog.close();
    };
  }, []);

  const title =
    target.kind === "course"
      ? t("courseAccess.dialog.courseTitle")
      : t("courseAccess.dialog.lectureTitle", { lecture: target.lecture.title });
  const description = t(
    target.kind === "course" ? "courseAccess.dialog.courseHelp" : "courseAccess.dialog.lectureHelp",
  );

  return (
    <dialog
      aria-describedby={descriptionId}
      aria-labelledby={titleId}
      aria-modal="true"
      className="course-access-dialog"
      ref={dialogRef}
      onCancel={(event) => {
        event.preventDefault();
        if (!saving) closeDialog();
      }}
    >
      <form
        className="course-access-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (customInvalid || (needsUniversityConfirmation && !confirmUniversityMembers)) return;
          onSave({ confirmUniversityMembers, inheritCourseDefault, rule });
        }}
      >
        <header className="course-access-dialog-header">
          <div>
            <h2 id={titleId}>{title}</h2>
            <p id={descriptionId}>{description}</p>
          </div>
          <button
            aria-label={t("courseAccess.cancel")}
            disabled={saving}
            type="button"
            onClick={closeDialog}
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <div className="course-access-dialog-body">
          {target.kind === "lecture" ? (
            <label className="course-access-inherit">
              <input
                checked={inheritCourseDefault}
                disabled={saving}
                type="checkbox"
                onChange={(event) => {
                  const inherit = event.target.checked;
                  setInheritCourseDefault(inherit);
                  setRule(editableAccessRule(target.workspace.accessSummary.default_rule));
                }}
              />
              <span>{t("courseAccess.useDefault")}</span>
            </label>
          ) : null}

          <CourseAccessFields
            disabled={saving || inheritCourseDefault}
            kind={target.kind}
            lectureDate={lecture?.date ?? ""}
            rule={rule}
            onChange={setRule}
          />

          {!inheritCourseDefault &&
          rule.audience !== "instructors_only" &&
          rule.publication_mode === "custom" ? (
            <label className="course-access-datetime">
              <span>{t("courseAccess.dateTime")}</span>
              <input
                aria-describedby={customInvalid ? customErrorId : undefined}
                aria-invalid={customInvalid}
                disabled={saving}
                type="datetime-local"
                value={datetimeLocalValue(rule.publication_at)}
                onChange={(event) =>
                  setRule({ ...rule, publication_at: publicationAtFromLocal(event.target.value) })
                }
              />
              <small>
                {t("courseAccess.timezone", {
                  zone: "Europe/Berlin",
                })}
              </small>
              {customInvalid ? (
                <span className="form-error" id={customErrorId}>
                  {t("courseAccess.customRequired")}
                </span>
              ) : null}
            </label>
          ) : null}

          <AccessPreview kind={target.kind} lecture={lecture} rule={rule} />

          {needsUniversityConfirmation ? (
            <label className="course-access-confirmation">
              <input
                checked={confirmUniversityMembers}
                disabled={saving}
                type="checkbox"
                onChange={(event) => setConfirmUniversityMembers(event.target.checked)}
              />
              <span>{t("courseAccess.confirmUniversity")}</span>
            </label>
          ) : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <footer className="course-access-dialog-footer">
          <button disabled={saving} type="button" onClick={closeDialog}>
            {t("courseAccess.cancel")}
          </button>
          <button
            className="primary-action"
            disabled={
              saving || customInvalid || (needsUniversityConfirmation && !confirmUniversityMembers)
            }
            type="submit"
          >
            {saving ? t("courseAccess.saving") : t("courseAccess.save")}
          </button>
        </footer>
      </form>
    </dialog>
  );

  function closeDialog() {
    onClose();
    window.setTimeout(() => document.getElementById(target.triggerId)?.focus(), 0);
  }
}

function initialRule(target: ProfessorAccessTarget) {
  if (target.kind === "course")
    return editableAccessRule(target.workspace.accessSummary.default_rule);
  return editableAccessRule(lectureSummary(target).rule);
}

function isInherited(target: ProfessorAccessTarget) {
  return target.kind === "lecture" && lectureSummary(target).rule_source === "course_default";
}

function lectureSummary(target: Extract<ProfessorAccessTarget, { kind: "lecture" }>) {
  const summary = target.workspace.accessSummary.lectures.find(
    (item) => item.lecture_id === target.lecture.id,
  );
  if (!summary) throw new Error(`Missing access summary for ${target.lecture.id}.`);
  return summary;
}

function AccessPreview({
  kind,
  lecture,
  rule,
}: {
  kind: ProfessorAccessTarget["kind"];
  lecture?: Lecture;
  rule: CourseAccessRule;
}) {
  const { locale, t } = useI18n();
  const audience = audienceLabel(rule.audience, t);
  const release = previewRelease(kind, lecture, rule, locale, t);
  return (
    <p className="course-access-preview" aria-live="polite">
      <strong>{audience}</strong>
      <span>{release}</span>
    </p>
  );
}

function previewRelease(
  kind: ProfessorAccessTarget["kind"],
  lecture: Lecture | undefined,
  rule: CourseAccessRule,
  locale: string,
  t: ReturnType<typeof useI18n>["t"],
) {
  if (rule.audience === "instructors_only" || rule.publication_mode === "hidden") {
    return t("courseAccess.status.hidden");
  }
  if (kind === "course" || !lecture) {
    return t(`courseAccess.release.${releaseKey(rule.publication_mode)}`);
  }

  const now = new Date();
  const availability = lectureAvailability(rule, lecture.date, true, now);
  if (!availability.availableAt || availability.state === "hidden") {
    return t("courseAccess.status.hidden");
  }
  const date = formatAccessDate(availability.availableAt, locale, true);
  if (availability.state === "scheduled") {
    return t("courseAccess.status.scheduled", {
      date,
      relative: formatRelativeAccess(availability.availableAt, locale, now),
    });
  }
  return t("courseAccess.status.availableSince", { date });
}

function audienceLabel(audience: CourseAccessRule["audience"], t: ReturnType<typeof useI18n>["t"]) {
  if (audience === "instructors_only") return t("courseAccess.audience.instructors");
  if (audience === "tuebingen_enrolled") return t("courseAccess.audience.course");
  if (audience === "platform_authenticated") return t("courseAccess.audience.university");
  return t("courseAccess.audience.public");
}

function releaseKey(mode: CourseAccessRule["publication_mode"]) {
  if (mode === "on_lecture_date") return "lectureDate" as const;
  if (mode === "published_now") return "now" as const;
  return mode;
}
