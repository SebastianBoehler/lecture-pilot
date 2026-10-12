import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";

import { getCourseLectures, getCourses, sendAgentTurnStream } from "../shared/api";
import { appendLiveToolTag, completePendingTutorMessage, pendingTutorMessage } from "./agentTurnUi";
import {
  defaultLessonPanel,
  initialCourseId,
  initialLecture,
  initialMessagesForAttendance,
  localDemoSession,
} from "../shell/appDefaults";
import { lessonKey, lessonPath, pathForView, type AppRoute } from "../shell/appRoute";
import { canManageCourses } from "../shared/authz";
import type { TutorMessageOptions } from "../canvas/canvasLearningActions";
import type { Locale } from "../i18n/i18n";
import { resetLearnerWorkspace } from "./learnerWorkspaceApi";
import * as publishedCanvas from "./publishedCanvasView";
import type { GateReviewOpening } from "../dashboard/reviewQueueTypes";
import {
  applyTutorSections,
  emptyCanvasNavigation,
  navigateForTutorCommands,
} from "./tutorCanvasCommands";
import type { CourseWorkspace } from "../dashboard/useCourseWorkspace";
import { useLessonState } from "./useLessonState";
import type { WorkspaceResetSelection } from "./WorkspaceResetControl";
import type {
  Attendance,
  CanvasDocument,
  ChatMessage,
  Lecture,
  LessonMode,
  LessonPanelMode,
  LoginSession,
} from "../shared/types";

type LessonSessionOptions = {
  route: AppRoute;
  session: LoginSession | null;
  enabled: boolean;
  locale: Locale;
  navigate: (path: string, options?: { replace?: boolean }) => void;
  workspace: CourseWorkspace;
  onTutorTurn: () => void;
};

/** Owns the open lecture: its canvas, tutor conversation and learner state. */
export function useLessonSession(options: LessonSessionOptions) {
  const { route, session, locale, navigate, workspace } = options;
  const [courseId, setCourseId] = useState(() => initialCourseId(route));
  const [lecture, setLecture] = useState(() => initialLecture(route));
  const [mode, setMode] = useState<LessonMode>(() =>
    route.view === "lesson" ? route.lessonMode : "learner",
  );
  const loadedLessonRoute = useRef<string | null>(null);
  const [panelMode, setPanelMode] = useState<LessonPanelMode | null>(() =>
    route.view === "lesson" ? defaultLessonPanel() : null,
  );
  const [canvasDocument, setCanvasDocument] = useState<CanvasDocument | null>(null);
  const [publishedCanvasView, setPublishedCanvasView] =
    useState<publishedCanvas.PublishedCanvasView | null>(null);
  const [canvasError, setCanvasError] = useState<string | null>(null);
  const [navigation, setNavigation] = useState(emptyCanvasNavigation);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastTutorModel, setLastTutorModel] = useState<string | null>(null);
  const lessonState = useLessonState({
    courseId,
    lectureId: lecture?.id ?? "",
    session,
    mode,
    enabled: options.enabled && Boolean(lecture),
  });
  const workspaceMode = mode === "professor-preview" ? "professor-preview" : "learner";

  function focusCanvas(focusedSectionId: string, highlightedBlockId: string | null = null) {
    setNavigation((current) => ({
      focusedSectionId,
      highlightedBlockId,
      highlightedText: null,
      version: current.version + 1,
    }));
  }

  const openLecture = useCallback(
    async (
      nextCourseId: string,
      nextLecture: Lecture,
      nextMode: LessonMode = "learner",
      updateRoute = true,
      review?: GateReviewOpening,
      focusSectionId?: string,
    ) => {
      loadedLessonRoute.current = lessonKey(nextCourseId, nextLecture.id, nextMode);
      if (updateRoute) navigate(lessonPath(nextCourseId, nextLecture.id, nextMode));
      setCourseId(nextCourseId);
      setLecture(nextLecture);
      setMode(nextMode);
      setPanelMode(defaultLessonPanel());
      setCanvasDocument(null);
      setPublishedCanvasView(null);
      setCanvasError(null);
      focusCanvas(review?.section_id ?? "", review?.gate_id ?? null);
      setMessages(initialMessagesForAttendance(nextLecture.attendance, review, locale));
      setLastTutorModel(null);

      try {
        if (nextCourseId !== workspace.courseId && session) {
          const [courses, courseLectures] = await Promise.all([
            getCourses(session),
            getCourseLectures(nextCourseId, session),
          ]);
          const course = courses.find((item) => item.id === nextCourseId);
          if (!course) throw new Error("This course could not be found.");
          workspace.showCourse(course, courseLectures);
        }
        const { document, publishedView } = await publishedCanvas.loadCanvasForMode(
          nextCourseId,
          nextLecture.id,
          session,
          nextMode,
        );
        setPublishedCanvasView(publishedView);
        setCanvasDocument(document);
        const searchedSection = document.sections.find((section) => section.id === focusSectionId);
        if (!review && searchedSection) {
          // Section anchors share the canvas id space; targeting one scrolls a search hit into view.
          focusCanvas(searchedSection.id, searchedSection.id);
        } else {
          const focusedSectionId = review?.section_id ?? document.sections[0]?.id ?? "";
          setNavigation((current) => ({ ...current, focusedSectionId }));
        }
      } catch (error) {
        setCanvasError(error instanceof Error ? error.message : "Canvas loading failed.");
      }
    },
    // workspace.showCourse is stable; only the loaded course id decides whether to reload it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [locale, navigate, session, workspace.courseId],
  );

  const restoreLessonRoute = useEffectEvent(
    async (nextRoute: Extract<AppRoute, { view: "lesson" }>) => {
      if (!session) return;
      if (nextRoute.lessonMode !== "learner" && !canManageCourses(session)) {
        loadedLessonRoute.current = null;
        navigate(pathForView("dashboard"), { replace: true });
        setPanelMode(null);
        setCanvasError("Lecture preview requires a course-management account.");
        return;
      }
      try {
        const [nextLectures, courses] = await Promise.all([
          getCourseLectures(nextRoute.courseId, session),
          getCourses(session),
        ]);
        const nextLecture = nextLectures.find((item) => item.id === nextRoute.lectureId);
        if (!nextLecture) throw new Error("This lecture could not be found.");
        const course = courses.find((item) => item.id === nextRoute.courseId);
        if (!course) throw new Error("This course could not be found.");
        workspace.showCourse(course, nextLectures);
        await openLecture(nextRoute.courseId, nextLecture, nextRoute.lessonMode, false);
      } catch (error) {
        loadedLessonRoute.current = null;
        setCanvasError(error instanceof Error ? error.message : "Canvas loading failed.");
      }
    },
  );

  useEffect(() => {
    if (route.view !== "lesson" || !session) return;
    const key = lessonKey(route.courseId, route.lectureId, route.lessonMode);
    if (loadedLessonRoute.current === key) return;
    loadedLessonRoute.current = key;
    void restoreLessonRoute(route);
  }, [route, session]);

  async function sendTutorMessage(message: string, messageOptions: TutorMessageOptions = {}) {
    if (!lecture) throw new Error("Open a lecture before asking the tutor.");
    const timestamp = Date.now();
    const userMessageId = `user-${timestamp}`;
    const pendingMessageId = `agent-pending-${timestamp}`;
    setMessages((current) => [
      ...current,
      { id: userMessageId, role: "user", content: message },
      pendingTutorMessage(pendingMessageId),
    ]);
    let result;
    try {
      result = await sendAgentTurnStream(
        {
          course_id: courseId,
          lecture_id: lecture.id,
          attendance: lecture.attendance,
          message,
          checkpoint_gate_id: messageOptions.checkpointGateId,
          canvas_state: {
            focused_section_id:
              messageOptions.focusedSectionId ?? (navigation.focusedSectionId || null),
          },
          locale,
        },
        session ?? localDemoSession,
        {
          onActivity: (tag) => {
            setMessages((current) => appendLiveToolTag(current, pendingMessageId, tag));
          },
          mode: workspaceMode,
        },
      );
    } catch (error) {
      setMessages((current) =>
        current.filter((item) => item.id !== userMessageId && item.id !== pendingMessageId),
      );
      throw error;
    }
    setLastTutorModel(result.model);
    setCanvasDocument((current) => applyTutorSections(current, result.canvas_commands));
    setNavigation((current) => navigateForTutorCommands(current, result.canvas_commands));
    setMessages((current) => completePendingTutorMessage(current, pendingMessageId, result));
    await lessonState.applyTutorResult(result);
    options.onTutorTurn();
  }

  async function resetWorkspace(selection: WorkspaceResetSelection) {
    if (!lecture) return;
    const activeSession = session ?? localDemoSession;
    await resetLearnerWorkspace(courseId, selection, activeSession, workspaceMode);
    if (selection.reset_progress) {
      workspace.resetAttendance();
      setLecture((current) => current && { ...current, attendance: "unknown" });
    }
    const publishedView = await publishedCanvas.getPublishedCanvasView(
      courseId,
      lecture.id,
      activeSession,
      workspaceMode,
    );
    setPublishedCanvasView(publishedView);
    setCanvasDocument(publishedView.document);
    setCanvasError(null);
    setNavigation((current) => ({
      ...current,
      focusedSectionId: publishedView.document.sections[0]?.id ?? "",
      highlightedBlockId: null,
      highlightedText: null,
    }));
    const attendance = selection.reset_progress ? "unknown" : lecture.attendance;
    setMessages(initialMessagesForAttendance(attendance, undefined, locale));
    setLastTutorModel(null);
    await lessonState.refresh();
    setNavigation((current) => ({ ...current, version: current.version + 1 }));
  }

  return {
    canvasDocument,
    canvasError,
    courseId,
    lastTutorModel,
    lecture,
    lessonState,
    messages,
    mode,
    navigation,
    panelMode,
    publishedCanvasView,
    openLecture,
    resetWorkspace,
    sendTutorMessage,
    setPanelMode,
    /** Selects the loaded course and keeps the open lecture when it still exists. */
    selectCourse(nextCourseId: string, lectures: Lecture[]) {
      setCourseId(nextCourseId);
      setLecture(
        (current) => lectures.find((item) => item.id === current?.id) ?? lectures[0] ?? null,
      );
    },
    setAttendance(lectureId: string, attendance: Attendance) {
      setLecture((current) => (current?.id === lectureId ? { ...current, attendance } : current));
    },
    /** Clears everything a signed-out user must not see. */
    clear() {
      setPanelMode(null);
      focusCanvas("");
      setCanvasDocument(null);
      setPublishedCanvasView(null);
      setCanvasError(null);
      setMessages([]);
      setLastTutorModel(null);
    },
  };
}

export type LessonSession = ReturnType<typeof useLessonSession>;
