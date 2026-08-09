import { apiUrl, getDraftLectureCanvas, readApiError } from "./api";
import { localDemoSession } from "./appDefaults";
import { learnerRequestInit } from "./authz";
import type { LearnerLessonState, LearnerQuizState } from "./learnerLessonStateTypes";
import type { CanvasDocument, LearnerWorkspaceMode, LoginSession } from "./types";

export type PublishedCanvasView = {
  document: CanvasDocument;
  publication_version: number;
  learning_map_revision: string;
};

export async function loadCanvasForMode(
  courseId: string,
  lectureId: string,
  session: LoginSession | null,
  mode: LearnerWorkspaceMode | "draft",
): Promise<{ document: CanvasDocument; publishedView: PublishedCanvasView | null }> {
  if (mode === "draft") {
    if (!session) throw new Error("Professor session is required to load a draft canvas.");
    return {
      document: await getDraftLectureCanvas(courseId, lectureId, session),
      publishedView: null,
    };
  }
  const publishedView = await getPublishedCanvasView(
    courseId,
    lectureId,
    session ?? localDemoSession,
    mode,
  );
  return { document: publishedView.document, publishedView };
}

export async function getPublishedCanvasView(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  mode: LearnerWorkspaceMode = "learner",
): Promise<PublishedCanvasView> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/canvas`),
    learnerRequestInit(session, mode),
  );
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas loading failed."));
  if (!isPublishedCanvasView(payload, courseId, lectureId)) {
    throw new Error("Published canvas response is invalid.");
  }
  return payload;
}

export function isPublishedCanvasView(
  payload: unknown,
  courseId: string,
  lectureId: string,
): payload is PublishedCanvasView {
  if (!isRecord(payload)) return false;
  return (
    Number.isInteger(payload.publication_version) &&
    Number(payload.publication_version) >= 1 &&
    typeof payload.learning_map_revision === "string" &&
    /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/.test(payload.learning_map_revision) &&
    isCanvasDocument(payload.document, courseId, lectureId)
  );
}

export function reconcileCanvasLearnerState(
  view: PublishedCanvasView | null,
  learnerState: LearnerLessonState | null,
): {
  publicationVersion: number | null;
  quizStates: Record<string, LearnerQuizState>;
  currentLearnerState: LearnerLessonState | null;
  requiresReconciliation: boolean;
} {
  if (!view) {
    return {
      publicationVersion: null,
      quizStates: {},
      currentLearnerState: null,
      requiresReconciliation: false,
    };
  }
  const current = learnerState?.publication_version === view.publication_version;
  return {
    publicationVersion: view.publication_version,
    quizStates: current && learnerState ? learnerState.quiz_states : {},
    currentLearnerState: current ? learnerState : null,
    requiresReconciliation: learnerState !== null && !current,
  };
}

function isCanvasDocument(payload: unknown, courseId: string, lectureId: string) {
  if (!isRecord(payload)) return false;
  return (
    typeof payload.id === "string" &&
    payload.course_id === courseId &&
    payload.lecture_id === lectureId &&
    typeof payload.title === "string" &&
    ["latex", "markdown", "generated"].includes(String(payload.source_kind)) &&
    typeof payload.source_ref === "string" &&
    Array.isArray(payload.sections)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
