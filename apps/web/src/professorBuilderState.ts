import type { LectureScheduleItem } from "./types";
import type { CourseAccessPolicy } from "./courseAccessTypes";

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
  bundleReady: boolean;
  canvasReady: boolean;
  lectureSchedule: LectureScheduleItem[];
  query: string;
};

const defaultCourseSetup: CourseSetup = {
  accessPolicy: "tuebingen_enrolled",
  courseTitle: "",
  lectureTitle: "",
  lectureNumber: "",
  lectureCount: "",
  firstLectureDate: "",
  target: "full-course",
};

const defaultFlow: SavedProfessorFlow = {
  setup: defaultCourseSetup,
  workspace: null,
  courseReady: false,
  bundleReady: false,
  canvasReady: false,
  lectureSchedule: [],
  query: "",
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
    if (isUntouchedLegacyDemoFlow(parsed)) return defaultFlow;
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

export function clearSavedFlow() {
  try {
    window.sessionStorage.removeItem(flowStorageKey);
  } catch {
  }
}

function isUntouchedLegacyDemoFlow(flow: Partial<SavedProfessorFlow>) {
  const setup = flow.setup;
  const hasLegacyDemoValue =
    setup?.courseTitle === "Grundlagen des Maschinellen Lernens" ||
    setup?.lectureNumber === "03" ||
    setup?.lectureTitle === "Bayesian Decision Theory" ||
    setup?.firstLectureDate === "2026-06-07" ||
    flow.query === "Bayesian decision theory machine learning Tübingen";
  return Boolean(
    !flow.workspace &&
    !flow.courseReady &&
    !flow.bundleReady &&
    !flow.canvasReady &&
    !flow.lectureSchedule?.length &&
    hasLegacyDemoValue,
  );
}
