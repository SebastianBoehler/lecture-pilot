import { formatAccessDate, formatRelativeAccess } from "./courseAccessStatus";
import { useI18n } from "./i18n";
import type { Attendance, Lecture } from "./types";

export function DashboardLectureRow({
  lecture,
  onOpen,
  onSetAttendance,
}: {
  lecture: Lecture;
  onOpen: (lecture: Lecture) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const { locale, t } = useI18n();
  const scheduled = lecture.releaseStatus === "scheduled";
  const availableAt = lecture.effectivePublicationAt
    ? new Date(lecture.effectivePublicationAt)
    : null;

  return (
    <article className={`lecture-row${scheduled ? " is-scheduled" : ""}`}>
      <div className="lecture-number">{lecture.number}</div>
      <div>
        <h3>{lecture.title}</h3>
        {scheduled && availableAt ? (
          <p className="lecture-release-time">
            {t("courseAccess.status.scheduled", {
              date: formatAccessDate(availableAt, locale, true),
              relative: formatRelativeAccess(availableAt, locale),
            })}
          </p>
        ) : (
          <>
            <p>
              {lecture.date} ·{" "}
              {t("dashboard.attendance", {
                status: attendanceLabel(lecture.attendance, t),
              })}
            </p>
            <div
              className="attendance-control"
              role="group"
              aria-label={t("dashboard.attendanceFor", { lecture: lecture.title })}
            >
              {(["present", "absent", "unknown"] as const).map((status) => (
                <button
                  aria-pressed={lecture.attendance === status}
                  className={lecture.attendance === status ? "is-active" : undefined}
                  key={status}
                  onClick={() => onSetAttendance(lecture.id, status)}
                  type="button"
                >
                  {attendanceLabel(status, t)}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
      {scheduled ? null : (
        <button type="button" onClick={() => onOpen(lecture)}>
          {t("dashboard.openLecture", { number: lecture.number })}
        </button>
      )}
    </article>
  );
}

function attendanceLabel(status: Attendance, t: ReturnType<typeof useI18n>["t"]) {
  if (status === "present") return t("attendance.present");
  if (status === "absent") return t("attendance.absent");
  return t("attendance.unknown");
}
