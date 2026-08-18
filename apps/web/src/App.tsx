import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";

import { getCourseLectures, publishLectureCanvas, sendAgentTurnStream } from "./api";
import {
  appendLiveToolTag,
  applyCanvasSection,
  completePendingTutorMessage,
  pendingTutorMessage,
} from "./agentTurnUi";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";
import { AppRoutes } from "./AppRoutes";
import { lessonKey, lessonPath, pathForView, requiresSession, type AppRoute } from "./appRoute";
import type { TutorMessageOptions } from "./canvasLearningActions";
import { FeedbackDialog } from "./FeedbackDialog";
import { ProfessorWalkthrough } from "./ProfessorWalkthrough";
import * as publishedCanvas from "./publishedCanvasView";
import {
  initialMessagesForAttendance,
  localDemoSession,
  localProfessorSession,
} from "./appDefaults";
import type { GateReviewOpening } from "./reviewQueueTypes";
import { canManageCourses } from "./authz";
import { clearDemoWorkspaceCourse, writeDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { I18nProvider, type Locale } from "./i18n";
import { resetLearnerWorkspace } from "./learnerWorkspaceApi";
import { readLocalePreference, writeLocalePreference } from "./localePreference";
import { useLessonState } from "./useLessonState";
import { clearSavedFlow } from "./professorBuilderState";
import { useStoredLoginSession } from "./loginSessionStorage";
import { lectures } from "./sampleData";
import { logoutSession } from "./sessionApi";
import { clearAllPracticeExamDrafts } from "./practiceExamDraft";
import { useAppRoute } from "./useAppRoute";
import { usePublishedLectures } from "./usePublishedLectures";
import { useUniversityCourseSync } from "./useUniversityCourseSync";
import { useFeedbackPrompt } from "./useFeedbackPrompt";
import { useViewTransitionReset } from "./useViewTransitionReset";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";
import { findLoadableWorkspaceCourse } from "./workspaceCourseLoader";
import type { WorkspaceResetSelection } from "./WorkspaceResetControl";
import type {
  Attendance,
  CanvasDocument,
  ChatMessage,
  LessonPanelMode,
  LessonMode,
  Lecture,
  LoginSession,
  Theme,
  UniversityCourse,
  View,
} from "./types";

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [locale, setLocale] = useState<Locale>(() => readLocalePreference());
  const { navigate, route } = useAppRoute();
  const [session, setSession, restoringSession] = useStoredLoginSession();
  const view = !session && requiresSession(route.view) ? "login" : route.view;
  const feedback = useFeedbackPrompt(session, view === "dashboard");
  const [availableLectures, setAvailableLectures] = useState(() =>
    import.meta.env.DEV ? lectures : [],
  );
  const [workspaceCourse, setWorkspaceCourse] = useState<UniversityCourse>(
    localDemoSession.courses[0],
  );
  const initialCourseId =
    route.view === "lesson" ? route.courseId : import.meta.env.DEV ? "martius-ml" : "";
  const [workspaceCourseId, setWorkspaceCourseId] = useState(initialCourseId);
  const [selectedCourseId, setSelectedCourseId] = useState(initialCourseId);
  const [selectedLecture, setSelectedLecture] = useState(() => initialLecture(route));
  const [lessonMode, setLessonMode] = useState<LessonMode>(() =>
    route.view === "lesson" ? route.lessonMode : "learner",
  );
  const loadedLessonRoute = useRef<string | null>(null);
  const [panelMode, setPanelMode] = useState<LessonPanelMode | null>(
    route.view === "lesson" ? "chat" : null,
  );
  const [canvasDocument, setCanvasDocument] = useState<CanvasDocument | null>(null);
  const [publishedCanvasView, setPublishedCanvasView] =
    useState<publishedCanvas.PublishedCanvasView | null>(null);
  const [canvasError, setCanvasError] = useState<string | null>(null);
  const [workspaceLoadError, setWorkspaceLoadError] = useState<string | null>(null);
  const [focusedSectionId, setFocusedSectionId] = useState("bayesian-decision-theory-the-aim");
  const [highlightedBlockId, setHighlightedBlockId] = useState<string | null>(null);
  const [highlightedText, setHighlightedText] = useState<string | null>(null);
  const [navigationVersion, setNavigationVersion] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessagesForAttendance(lectures[2].attendance),
  );
  useVersionUpdateActivity(messages.some((message) => Boolean(message.isPending)));
  const [lastTutorModel, setLastTutorModel] = useState<string | null>(null);
  const lessonState = useLessonState({
    courseId: selectedCourseId,
    lectureId: selectedLecture.id,
    session,
    mode: lessonMode,
    enabled: view === "lesson",
  });
  const [publishedLectureIds, setPublishedLectureIds] = usePublishedLectures(availableLectures);
  useUniversityCourseSync(session, setSession);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = locale;
    writeLocalePreference(locale);
  }, [locale]);

  useEffect(() => {
    if (session && route.view === "login") {
      navigate(pathForView(landingView(session)), { replace: true });
      setPanelMode(null);
    }
  }, [navigate, route.view, session]);

  useEffect(() => {
    if (!restoringSession && !session && requiresSession(route.view)) {
      navigate(pathForView("login"), { replace: true });
    }
  }, [navigate, restoringSession, route.view, session]);

  useViewTransitionReset(view);

  const loadWorkspaceCourseFromSession = useEffectEvent((activeSession: LoginSession) =>
    loadWorkspaceCourse(activeSession, workspaceCourseId),
  );
  const shouldLoadWorkspaceFromSession = route.view !== "lesson";

  useEffect(() => {
    if (
      !session ||
      session.university_course_sync_status === "loading" ||
      !shouldLoadWorkspaceFromSession
    )
      return;
    void loadWorkspaceCourseFromSession(session);
  }, [session, shouldLoadWorkspaceFromSession]);

  async function loadWorkspaceCourse(
    activeSession: LoginSession,
    preferredCourseId = workspaceCourseId,
  ) {
    try {
      const loaded = await findLoadableWorkspaceCourse(activeSession, preferredCourseId);
      setWorkspaceLoadError(null);
      if (!loaded) {
        setAvailableLectures([]);
        return;
      }
      setWorkspaceCourse(loaded.course);
      setWorkspaceCourseId(loaded.course.id);
      setSelectedCourseId(loaded.course.id);
      setAvailableLectures(loaded.lectures);
      setSelectedLecture(
        (current) =>
          loaded.lectures.find((lecture) => lecture.id === current.id) ?? loaded.lectures[0],
      );
    } catch (error) {
      setAvailableLectures([]);
      setWorkspaceLoadError(
        error instanceof Error ? error.message : "Course workspace loading failed.",
      );
    }
  }
  async function handleTutorMessage(message: string, options: TutorMessageOptions = {}) {
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
          course_id: selectedCourseId,
          lecture_id: selectedLecture.id,
          attendance: selectedLecture.attendance,
          message,
          checkpoint_gate_id: options.checkpointGateId,
          canvas_state: { focused_section_id: options.focusedSectionId ?? focusedSectionId },
        },
        session ?? localDemoSession,
        {
          onActivity: (tag) => {
            setMessages((current) => appendLiveToolTag(current, pendingMessageId, tag));
          },
          mode: lessonMode === "professor-preview" ? "professor-preview" : "learner",
        },
      );
    } catch (error) {
      setMessages((current) =>
        current.filter((item) => item.id !== userMessageId && item.id !== pendingMessageId),
      );
      throw error;
    }
    setLastTutorModel(result.model);
    let nextFocusSectionId: string | null = null;
    let nextHighlightBlockId: string | null = null;
    let nextHighlightSectionId: string | null = null;
    let nextHighlightText: string | null = null;
    let generatedSectionId: string | null = null;
    for (const command of result.canvas_commands) {
      const section = command.section;
      if ((command.type === "append_section" || command.type === "update_section") && section) {
        setCanvasDocument((current) => applyCanvasSection(current, section, command.placement));
        generatedSectionId = command.section_id ?? section.id;
      }
      if (command.type === "focus_section" && command.section_id) {
        nextFocusSectionId = command.section_id;
      }
      if (command.type === "highlight_span" && command.span_id) {
        nextHighlightBlockId = command.span_id;
        nextHighlightSectionId = command.section_id ?? null;
        nextHighlightText = command.highlight_text ?? null;
      }
    }
    const navigationTargetId = nextFocusSectionId ?? generatedSectionId;
    if (
      navigationTargetId &&
      nextHighlightSectionId &&
      nextHighlightSectionId !== navigationTargetId
    ) {
      nextHighlightBlockId = null;
      nextHighlightText = null;
    }
    if (navigationTargetId) {
      setFocusedSectionId(navigationTargetId);
    }
    setHighlightedBlockId(nextHighlightBlockId);
    setHighlightedText(nextHighlightText);
    if (navigationTargetId || nextHighlightBlockId) {
      setNavigationVersion((current) => current + 1);
    }

    setMessages((current) => completePendingTutorMessage(current, pendingMessageId, result));
    await lessonState.applyTutorResult(result);
    feedback.recordSuccessfulTutorTurn();
  }

  function handleLogout() {
    if (session) void logoutSession(session);
    setSession(null);
    clearSavedFlow();
    clearAllPracticeExamDrafts();
    navigate(pathForView("login"), { replace: true });
    setPanelMode(null);
    setFocusedSectionId("bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setNavigationVersion((current) => current + 1);
    setCanvasDocument(null);
    setPublishedCanvasView(null);
    setCanvasError(null);
    setWorkspaceLoadError(null);
    setMessages(initialMessagesForAttendance(lectures[2].attendance));
    setLastTutorModel(null);
  }

  const handleOpenLecture = useCallback(
    async (
      courseId: string,
      lecture: Lecture,
      mode: LessonMode = "learner",
      updateRoute = true,
      review?: GateReviewOpening,
    ) => {
      loadedLessonRoute.current = lessonKey(courseId, lecture.id, mode);
      if (updateRoute) navigate(lessonPath(courseId, lecture.id, mode));
      setSelectedCourseId(courseId);
      setSelectedLecture(lecture);
      setLessonMode(mode);
      setPanelMode("chat");
      setCanvasDocument(null);
      setPublishedCanvasView(null);
      setCanvasError(null);
      setFocusedSectionId(review?.section_id ?? "bayesian-decision-theory-the-aim");
      setHighlightedBlockId(review?.gate_id ?? null);
      setHighlightedText(null);
      setNavigationVersion((current) => current + 1);
      setMessages(initialMessagesForAttendance(lecture.attendance, review));
      setLastTutorModel(null);

      try {
        const { document, publishedView } = await publishedCanvas.loadCanvasForMode(
          courseId,
          lecture.id,
          session,
          mode,
        );
        setPublishedCanvasView(publishedView);
        setCanvasDocument(document);
        setFocusedSectionId(
          review?.section_id ?? document.sections[0]?.id ?? "bayesian-decision-theory-the-aim",
        );
      } catch (error) {
        setCanvasError(error instanceof Error ? error.message : "Canvas loading failed.");
      }
    },
    [navigate, session],
  );

  const restoreLessonRoute = useEffectEvent(
    async (nextRoute: Extract<AppRoute, { view: "lesson" }>) => {
      if (!session) return;
      if (nextRoute.lessonMode !== "learner" && !canManageCourses(session)) {
        loadedLessonRoute.current = null;
        changeView("dashboard", true);
        setCanvasError("Lecture preview requires a course-management account.");
        return;
      }
      try {
        const nextLectures = await getCourseLectures(nextRoute.courseId, session);
        const lecture = nextLectures.find((item) => item.id === nextRoute.lectureId);
        if (!lecture) throw new Error("This lecture could not be found.");
        const course = session.courses.find((item) => item.id === nextRoute.courseId);
        if (course) setWorkspaceCourse(course);
        setWorkspaceCourseId(nextRoute.courseId);
        setAvailableLectures(nextLectures);
        await handleOpenLecture(nextRoute.courseId, lecture, nextRoute.lessonMode, false);
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

  function handleSetAttendance(lectureId: string, attendance: Attendance) {
    setAvailableLectures((current) =>
      current.map((lecture) => (lecture.id === lectureId ? { ...lecture, attendance } : lecture)),
    );
    if (selectedLecture.id === lectureId) {
      setSelectedLecture((current) => ({ ...current, attendance }));
    }
  }

  function handleWorkspaceDeleted(courseId: string) {
    clearDemoWorkspaceCourse(courseId);
    clearSavedFlow();
    setPublishedLectureIds([]);
    if (workspaceCourseId === courseId || selectedCourseId === courseId) {
      void loadWorkspaceCourse(
        session ?? localDemoSession,
        import.meta.env.DEV ? localDemoSession.courses[0].id : "",
      );
    }
  }

  async function handleResetWorkspace(options: WorkspaceResetSelection) {
    const activeSession = session ?? localDemoSession;
    const workspaceMode = lessonMode === "professor-preview" ? "professor-preview" : "learner";
    await resetLearnerWorkspace(selectedCourseId, options, activeSession, workspaceMode);
    if (options.reset_progress) {
      setAvailableLectures((current) =>
        current.map((lecture) => ({ ...lecture, attendance: "unknown" })),
      );
      setSelectedLecture((current) => ({ ...current, attendance: "unknown" }));
    }
    const publishedView = await publishedCanvas.getPublishedCanvasView(
      selectedCourseId,
      selectedLecture.id,
      activeSession,
      workspaceMode,
    );
    const document = publishedView.document;
    setPublishedCanvasView(publishedView);
    setCanvasDocument(document);
    setCanvasError(null);
    setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setMessages(
      initialMessagesForAttendance(options.reset_progress ? "unknown" : selectedLecture.attendance),
    );
    setLastTutorModel(null);
    await lessonState.refresh();
    setNavigationVersion((current) => current + 1);
  }

  const courseManagerSession = canManageCourses(session) ? session : null;

  function changeView(nextView: View, replace = false) {
    if (nextView === "lesson") return;
    navigate(pathForView(nextView), { replace });
    setPanelMode(null);
  }

  return (
    <I18nProvider locale={locale} setLocale={setLocale}>
      <div className="app-shell">
        <AppHeader
          activeView={view}
          session={session}
          theme={theme}
          onBrand={() => {
            changeView(landingView(session));
          }}
          onOpenDashboard={() => {
            changeView(session ? "dashboard" : "login");
          }}
          onOpenPerformance={() => {
            if (courseManagerSession) {
              changeView("performance");
            }
          }}
          onOpenUsage={() => {
            if (courseManagerSession) {
              changeView("usage");
            }
          }}
          onOpenCourseManagement={() => {
            if (courseManagerSession) {
              changeView("course-management");
            }
          }}
          onOpenProfile={() => {
            changeView("profile");
          }}
          onOpenProfessor={() => {
            if (courseManagerSession) {
              changeView("professor");
            }
          }}
          onOpenFeedback={feedback.openManually}
          onToggleTheme={() => setTheme(theme === "light" ? "dark" : "light")}
        />
        {session && feedback.source ? (
          <FeedbackDialog
            accountType={session.account_type ?? "student"}
            context={
              view === "lesson"
                ? {
                    courseTitle: workspaceCourse.title,
                    lectureTitle: selectedLecture.title,
                  }
                : {}
            }
            open
            source={feedback.source}
            onClose={feedback.close}
          />
        ) : null}
        {courseManagerSession && view !== "lesson" ? (
          <ProfessorWalkthrough
            key={courseManagerSession.username}
            onViewChange={(nextView) => {
              changeView(nextView);
            }}
            username={courseManagerSession.username}
          />
        ) : null}

        <AppRoutes
          availableLectures={availableLectures}
          canvasDocument={canvasDocument}
          publishedCanvasView={publishedCanvasView}
          canvasError={canvasError}
          courseManagerSession={courseManagerSession}
          focusedSectionId={focusedSectionId}
          highlightedBlockId={highlightedBlockId}
          highlightedText={highlightedText}
          lastTutorModel={lastTutorModel}
          lessonMode={lessonMode}
          messages={messages}
          navigationVersion={navigationVersion}
          panelMode={panelMode}
          learnerState={lessonState.state}
          learnerStateError={lessonState.error}
          publishedLectureIds={publishedLectureIds}
          restoringSession={restoringSession}
          selectedCourseId={selectedCourseId}
          selectedLecture={selectedLecture}
          route={route}
          session={session}
          view={view}
          workspaceCourse={workspaceCourse}
          workspaceCourseId={workspaceCourseId}
          workspaceLoadError={workspaceLoadError}
          onLogout={handleLogout}
          onLogin={(nextSession) => {
            setSession(nextSession);
            if (route.view === "login") changeView(landingView(nextSession), true);
          }}
          onOpenDemo={() => {
            setSession(localDemoSession);
            if (route.view === "login") changeView("dashboard", true);
          }}
          onOpenProfessorDemo={() => {
            setSession(localProfessorSession);
            if (route.view === "login") changeView("professor", true);
          }}
          onOpenLecture={(courseId, lecture, review) => {
            void handleOpenLecture(courseId, lecture, "learner", true, review);
          }}
          onPreviewLecture={(courseId, lecture) => {
            void handleOpenLecture(courseId, lecture, "professor-preview");
          }}
          onNavigatePath={navigate}
          onSetAttendance={handleSetAttendance}
          onPublishWorkspace={async (courseId, lectureId) => {
            if (!courseManagerSession)
              throw new Error("Course management requires a professor account.");
            const result = await publishLectureCanvas(courseId, lectureId, courseManagerSession);
            setPublishedLectureIds((current) => Array.from(new Set([...current, lectureId])));
            return result;
          }}
          onWorkspacePublished={(course, nextLectures) => {
            if (!nextLectures.length) return;
            const publishedLectures = nextLectures.map((lecture) => ({
              ...lecture,
              contentReady: true,
            }));
            writeDemoWorkspaceCourse(course);
            setWorkspaceCourse(course);
            setWorkspaceLoadError(null);
            setWorkspaceCourseId(course.id);
            setSelectedCourseId(course.id);
            setAvailableLectures(publishedLectures);
            setSelectedLecture(
              (current) =>
                publishedLectures.find((lecture) => lecture.id === current.id) ??
                publishedLectures[0],
            );
            setPublishedLectureIds(publishedLectures.map((lecture) => lecture.id));
          }}
          onWorkspaceDeleted={handleWorkspaceDeleted}
          onViewChange={changeView}
          onSendMessage={handleTutorMessage}
          onPracticeSubmitted={lessonState.applyQuizResult}
          onResetWorkspace={handleResetWorkspace}
          onTogglePanel={(mode) => {
            setPanelMode((current) => (current === mode ? null : mode));
          }}
        />
        {!restoringSession && view !== "lesson" ? (
          <AppFooter
            onOpenChangelog={() => changeView("changelog")}
            onOpenHowItWorks={() => changeView("how-it-works")}
            onOpenLearningScience={() => changeView("learning-science")}
            onOpenPrivacy={() => changeView("privacy")}
          />
        ) : null}
      </div>
    </I18nProvider>
  );
}

export default App;

function landingView(session: LoginSession | null): Exclude<View, "lesson"> {
  if (!session) return "login";
  if ((session.account_type ?? "student") === "professor") {
    return canManageCourses(session) ? "professor" : "profile";
  }
  return "dashboard";
}

function initialLecture(route: AppRoute) {
  if (route.view !== "lesson") return lectures[2];
  return (
    lectures.find((lecture) => lecture.id === route.lectureId) ?? {
      id: route.lectureId,
      number: route.lectureId.replace(/^lecture-/, ""),
      title: "Lecture",
      date: "",
      attendance: "unknown" as Attendance,
    }
  );
}
