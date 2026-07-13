import type { CourseWorkspaceResult } from "./types";

export type CourseUpdateFileChange = {
  path: string;
  kind: string;
  size_bytes: number;
  sha256: string;
  status: "new" | "changed";
};

export type CourseUpdateLectureCandidate = {
  candidate_id: string;
  action: "new" | "update";
  lecture_id?: string | null;
  number: string;
  title: string;
  date: string;
  file_paths: string[];
};

export type CourseUpdateLectureOption = {
  lecture_id: string;
  number: string;
  title: string;
  date: string;
};

export type CourseUpdateAnalysis = {
  course_id: string;
  update_id: string;
  candidates: CourseUpdateLectureCandidate[];
  existing_lectures: CourseUpdateLectureOption[];
  unassigned_files: CourseUpdateFileChange[];
  unchanged_files: number;
};

export type CourseUpdateLectureSelection = {
  lecture_id?: string | null;
  number: string;
  title: string;
  date: string;
  file_paths: string[];
};

export type CourseUpdateApplyResult = {
  course_id: string;
  update_id: string;
  applied_files: number;
  affected_lecture_ids: string[];
  workspace: CourseWorkspaceResult;
};
