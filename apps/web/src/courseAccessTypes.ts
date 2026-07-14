export type CourseAccessPolicy =
  "instructors_only" | "tuebingen_enrolled" | "platform_authenticated" | "public";

export type CourseDefaultPublicationMode = "hidden" | "on_lecture_date";

export type LecturePublicationMode = CourseDefaultPublicationMode | "custom" | "published_now";

export type CourseAccessRule = {
  audience: CourseAccessPolicy;
  publication_mode: LecturePublicationMode;
  publication_at: string | null;
};

export type LectureReleaseStatus = "hidden" | "scheduled" | "released";

export type LectureAccessSummary = {
  lecture_id: string;
  rule_source: "course_default" | "lecture_override";
  rule: CourseAccessRule;
  effective_publication_at: string | null;
  release_status: LectureReleaseStatus;
  content_ready: boolean;
};

export type CourseAccessSummary = {
  course_id: string;
  default_rule: CourseAccessRule;
  lectures: LectureAccessSummary[];
};

export type CourseAccessTarget =
  { courseId: string; kind: "course" } | { courseId: string; kind: "lecture"; lectureId: string };

export type CourseAccessSaveInput = {
  confirmUniversityMembers: boolean;
  inheritCourseDefault: boolean;
  rule: CourseAccessRule;
};
