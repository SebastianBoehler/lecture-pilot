import type { CourseWorkspaceResult, LectureScheduleItem } from "../shared/types";
import type { CourseAccessPolicy } from "./courseAccessTypes";

export type BuilderTarget = "single-lecture" | "full-course";

export type CourseSetup = {
  accessPolicy: CourseAccessPolicy;
  canvasLanguage: "de" | "en";
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

export const defaultCourseSetup: CourseSetup = {
  accessPolicy: "tuebingen_enrolled",
  canvasLanguage: "en",
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
  } catch {}
}

export function writeResumeFlow(workspace: CourseWorkspaceResult) {
  const { course, lectures, active_lecture_id } = workspace;
  const single = resumeTarget(workspace) === "single-lecture" ? lectures[0] : null;
  writeSavedFlow({
    ...defaultFlow,
    setup: {
      ...defaultCourseSetup,
      accessPolicy: course.access_policy ?? defaultCourseSetup.accessPolicy,
      canvasLanguage: course.canvas_language ?? defaultCourseSetup.canvasLanguage,
      courseTitle: course.title,
      lectureTitle: single?.title ?? "",
      lectureNumber: single?.number ?? "",
      target: single ? "single-lecture" : "full-course",
    },
    workspace: { courseId: course.id, lectureId: active_lecture_id || lectures[0]?.id || "" },
    courseReady: true,
    // Backend restore decides the actual step from uploads, routing, plans and drafts.
    bundleReady: true,
  });
}

function resumeTarget({ lectures, setup_target }: CourseWorkspaceResult): BuilderTarget {
  if (setup_target) return setup_target;
  // Older courses: full-course setup starts with "Lecture NN" placeholders.
  const [only] = lectures;
  return lectures.length === 1 && !/^Lecture \d+$/.test(only.title)
    ? "single-lecture"
    : "full-course";
}

export function clearSavedFlow() {
  try {
    window.sessionStorage.removeItem(flowStorageKey);
  } catch {}
}
