import { apiUrl, readApiError } from "./api";
import { courseManagerHeaders } from "./authz";
import type { CourseSetup } from "./professorBuilderState";
import type {
  CourseWorkspaceResult,
  LectureScheduleItem,
  LectureScheduleProposal,
  LoginSession,
  SourceBundleManifest,
  YoutubeVideoCandidate,
} from "./types";

export async function createCourseWorkspace(
  setup: CourseSetup,
  session: LoginSession,
  lectures: LectureScheduleItem[] = [],
): Promise<CourseWorkspaceResult> {
  const response = await fetch(apiUrl("/admin/course-workspaces"), {
    method: "POST",
    headers: { ...courseManagerHeaders(session), "Content-Type": "application/json" },
    body: JSON.stringify({
      course_title: setup.courseTitle,
      lecture_title: setup.lectureTitle,
      lecture_number: setup.lectureNumber,
      lecture_count: Number(setup.lectureCount) || null,
      lectures,
      target: setup.target,
    }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Course workspace creation failed."));
  return payload as CourseWorkspaceResult;
}

export async function proposeLectureSchedule(input: {
  courseId: string;
  count?: number | null;
  firstLectureDate?: string;
  session: LoginSession;
}): Promise<LectureScheduleProposal> {
  const params = new URLSearchParams();
  if (input.firstLectureDate) params.set("first_lecture_date", input.firstLectureDate);
  if (input.count) params.set("count", String(input.count));
  const query = params.toString();
  const response = await fetch(
    apiUrl(`/admin/courses/${input.courseId}/lecture-schedule${query ? `?${query}` : ""}`),
    { headers: courseManagerHeaders(input.session) },
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Lecture schedule proposal failed."));
  return payload as LectureScheduleProposal;
}

export async function getSourceBundle(courseId: string, session: LoginSession): Promise<SourceBundleManifest> {
  const response = await fetch(apiUrl(`/courses/${courseId}/source-bundle`), {
    headers: courseManagerHeaders(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Source scan failed."));
  return payload as SourceBundleManifest;
}

export async function uploadCourseMaterial(input: {
  courseId: string;
  path: string;
  file: File;
  session: LoginSession;
}) {
  const body = new FormData();
  body.append("path", input.path);
  body.append("file", input.file);
  const response = await fetch(apiUrl(`/admin/courses/${input.courseId}/materials`), {
    method: "POST",
    headers: courseManagerHeaders(input.session),
    body,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Material upload failed."));
  return payload as { path: string; kind: string; size_bytes: number };
}

export async function searchYoutubeMedia(courseId: string, query: string, session: LoginSession) {
  const params = new URLSearchParams({ q: query, max_results: "5" });
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/media/youtube/search?${params}`), {
    headers: courseManagerHeaders(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "YouTube search failed."));
  return payload as { items: YoutubeVideoCandidate[] };
}

export async function includeYoutubeMedia(input: {
  courseId: string;
  lectureId: string;
  sectionId: string | null;
  video: YoutubeVideoCandidate;
  session: LoginSession;
}) {
  const response = await fetch(
    apiUrl(`/admin/courses/${input.courseId}/lectures/${input.lectureId}/media/youtube`),
    {
      method: "POST",
      headers: { ...courseManagerHeaders(input.session), "Content-Type": "application/json" },
      body: JSON.stringify({ section_id: input.sectionId, video: input.video }),
    },
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "YouTube include failed."));
  return payload as { block_id: string };
}
