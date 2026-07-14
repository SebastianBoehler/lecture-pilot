import { formatAccessDate, formatRelativeAccess } from "./courseAccessStatus";
import { useI18n } from "./i18n";
import type {
  CourseAccessPolicy,
  CourseAccessRule,
  LectureAccessSummary,
} from "./courseAccessTypes";

export function ProfessorLectureAccessStatus({
  now,
  summary,
}: {
  now?: Date;
  summary: LectureAccessSummary;
}) {
  const { locale, t } = useI18n();
  const accessLabel = releaseStatusLabel(summary, locale, t, now);
  return (
    <span className="created-lecture-access-status">
      <span>
        <strong>
          {summary.content_ready
            ? t("courseAccess.status.published")
            : t("courseAccess.status.draft")}
        </strong>
        <span aria-hidden="true"> · </span>
        {accessAudienceLabel(summary.rule.audience, t)}
      </span>
      <span>{accessLabel}</span>
      <small>
        {summary.rule_source === "course_default"
          ? t("courseAccess.status.inherited")
          : t("courseAccess.status.custom")}
        {!summary.content_ready ? ` · ${t("courseAccess.status.afterPublish")}` : ""}
      </small>
    </span>
  );
}

export function accessAudienceLabel(
  audience: CourseAccessPolicy,
  t: ReturnType<typeof useI18n>["t"],
) {
  if (audience === "instructors_only") return t("courseAccess.audience.instructors");
  if (audience === "tuebingen_enrolled") return t("courseAccess.audience.course");
  if (audience === "platform_authenticated") return t("courseAccess.audience.university");
  return t("courseAccess.audience.public");
}

export function defaultReleaseLabel(rule: CourseAccessRule, t: ReturnType<typeof useI18n>["t"]) {
  if (rule.audience === "instructors_only" || rule.publication_mode === "hidden") {
    return t("courseAccess.release.hidden");
  }
  return t("courseAccess.release.lectureDate");
}

function releaseStatusLabel(
  summary: LectureAccessSummary,
  locale: string,
  t: ReturnType<typeof useI18n>["t"],
  now = new Date(),
) {
  if (summary.rule.audience === "instructors_only" || summary.release_status === "hidden") {
    return t("courseAccess.status.hidden");
  }
  if (!summary.effective_publication_at) return t("courseAccess.status.availableNow");
  const publicationAt = new Date(summary.effective_publication_at);
  const formatted = formatAccessDate(publicationAt, locale, true);
  if (summary.release_status === "scheduled") {
    return t("courseAccess.status.scheduled", {
      date: formatted,
      relative: formatRelativeAccess(publicationAt, locale, now),
    });
  }
  return t("courseAccess.status.availableSince", { date: formatted });
}
