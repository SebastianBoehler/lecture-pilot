import {
  Building2,
  CalendarClock,
  Clock3,
  FilePenLine,
  Globe2,
  LockKeyhole,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

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
  const visibility = audiencePresentation(summary.rule.audience, t);
  const availability = availabilityPresentation(summary, locale, t, now);
  return (
    <span className="created-lecture-access-status">
      <span
        aria-label={visibility.label}
        className="created-lecture-visibility"
        title={visibility.label}
      >
        <visibility.Icon aria-hidden="true" size={15} strokeWidth={1.8} />
        <span>{visibility.shortLabel}</span>
      </span>
      <span className={`created-lecture-availability is-${availability.state}`}>
        <availability.Icon aria-hidden="true" size={15} strokeWidth={1.8} />
        <span>
          <strong>{availability.primary}</strong>
          {availability.detail ? <small>{availability.detail}</small> : null}
        </span>
      </span>
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

function audiencePresentation(
  audience: CourseAccessPolicy,
  t: ReturnType<typeof useI18n>["t"],
): { Icon: LucideIcon; label: string; shortLabel: string } {
  if (audience === "instructors_only") {
    return {
      Icon: LockKeyhole,
      label: accessAudienceLabel(audience, t),
      shortLabel: t("courseAccess.audience.privateShort"),
    };
  }
  if (audience === "tuebingen_enrolled") {
    return {
      Icon: UsersRound,
      label: accessAudienceLabel(audience, t),
      shortLabel: t("courseAccess.audience.courseShort"),
    };
  }
  if (audience === "platform_authenticated") {
    return {
      Icon: Building2,
      label: accessAudienceLabel(audience, t),
      shortLabel: t("courseAccess.audience.universityShort"),
    };
  }
  return {
    Icon: Globe2,
    label: accessAudienceLabel(audience, t),
    shortLabel: t("courseAccess.audience.publicShort"),
  };
}

function availabilityPresentation(
  summary: LectureAccessSummary,
  locale: string,
  t: ReturnType<typeof useI18n>["t"],
  now?: Date,
): { Icon: LucideIcon; detail: string | null; primary: string; state: string } {
  const accessLabel = releaseStatusLabel(summary, locale, t, now);
  if (!summary.content_ready) {
    return {
      Icon: FilePenLine,
      primary: t("courseAccess.status.draft"),
      detail: `${accessLabel} · ${t("courseAccess.status.afterPublish")}`,
      state: "draft",
    };
  }
  if (summary.release_status === "hidden") {
    return { Icon: LockKeyhole, primary: accessLabel, detail: null, state: "hidden" };
  }
  if (summary.release_status === "scheduled") {
    return { Icon: CalendarClock, primary: accessLabel, detail: null, state: "scheduled" };
  }
  return { Icon: Clock3, primary: accessLabel, detail: null, state: "available" };
}
