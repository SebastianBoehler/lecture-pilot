export type UniversityEnrollmentCourse = {
  source: "alma" | "ilias";
  external_course_id: string;
  term: string;
  title: string;
  number?: string | null;
  organization?: string | null;
  instructor?: string | null;
  display_url?: string | null;
};
