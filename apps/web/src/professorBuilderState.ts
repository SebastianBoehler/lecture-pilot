import type { LectureScheduleItem } from "./types";
import type { CourseAccessPolicy } from "./types";

export type BuilderTarget = "single-lecture" | "full-course";

export type CourseSetup = {
  accessPolicy: CourseAccessPolicy;
  courseTitle: string;
  lectureTitle: string;
  lectureNumber: string;
  lectureCount: string;
  firstLectureDate: string;
  target: BuilderTarget;
};

export type CourseWorkspaceState = {
  courseId: string;
  lectureId: string;
};

export type SavedProfessorFlow = {
  setup: CourseSetup;
  workspace: CourseWorkspaceState | null;
  courseReady: boolean;
  uploadPath: string;
  bundleReady: boolean;
  canvasReady: boolean;
  lectureSchedule: LectureScheduleItem[];
  query: string;
};

export const defaultCourseSetup: CourseSetup = {
  accessPolicy: "tuebingen_enrolled",
  courseTitle: "Grundlagen des Maschinellen Lernens",
  lectureTitle: "Bayesian Decision Theory",
  lectureNumber: "03",
  lectureCount: "",
  firstLectureDate: new Date().toISOString().slice(0, 10),
  target: "single-lecture",
};

export const defaultFlow: SavedProfessorFlow = {
  setup: defaultCourseSetup,
  workspace: null,
  courseReady: false,
  uploadPath: "uploads",
  bundleReady: false,
  canvasReady: false,
  lectureSchedule: [],
  query: "Bayesian decision theory machine learning Tübingen",
};

const flowStorageKey = "lecturepilot.professor-builder.current";

export function isCourseSetupReady(setup: CourseSetup) {
  if (!setup.courseTitle.trim()) return false;
  if (setup.target === "full-course") return true;
  return Boolean(setup.lectureNumber.trim() && setup.lectureTitle.trim());
}

export function readSavedFlow(): SavedProfessorFlow {
  if (typeof window === "undefined") return defaultFlow;
  try {
    const saved = window.sessionStorage.getItem(flowStorageKey);
    if (!saved) return defaultFlow;
    const parsed = JSON.parse(saved) as Partial<SavedProfessorFlow>;
    return {
      ...defaultFlow,
      ...parsed,
      setup: { ...defaultFlow.setup, ...parsed.setup },
    };
  } catch {
    return defaultFlow;
  }
}

export function writeSavedFlow(flow: SavedProfessorFlow) {
  try {
    window.sessionStorage.setItem(flowStorageKey, JSON.stringify(flow));
  } catch {
  }
}
