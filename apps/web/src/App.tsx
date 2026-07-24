import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";

import {
  getCourses,
  getCourseLectures,
  getDraftLectureCanvas,
  getLectureCanvas,
  publishLectureCanvas,
  sendAgentTurnStream,
} from "./api";
import {
  appendLiveToolTag,
  applyCanvasSection,
  completePendingTutorMessage,
  pendingTutorMessage,
} from "./agentTurnUi";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";
import { AppRoutes } from "./AppRoutes";
import { lessonPath, pathForView, requiresSession, type AppRoute } from "./appRoute";
import { FeedbackDialog } from "./FeedbackDialog";
import { ProfessorWalkthrough } from "./ProfessorWalkthrough";
import {
  initialMessagesForAttendance,
  localDemoSession,
  localProfessorSession,
} from "./appDefaults";
import { canManageCourses } from "./authz";
import {
  clearDemoWorkspaceCourse,
  readDemoWorkspaceCourse,
  writeDemoWorkspaceCourse,
} from "./demoWorkspaceAccess";
import { developmentWorkspaceCourse } from "./devWorkspaceAccess";
import { I18nProvider, type Locale } from "./i18n";
import { resetLearnerWorkspace } from "./learnerWorkspaceApi";
import { readLocalePreference, writeLocalePreference } from "./localePreference";
import { clearSavedFlow } from "./professorBuilderState";
import { useStoredLoginSession } from "./loginSessionStorage";
import { lectures } from "./sampleData";
import { logoutSession } from "./sessionApi";
import { useAppRoute } from "./useAppRoute";
import { usePublishedLectures } from "./usePublishedLectures";
import { useUniversityCourseSync } from "./useUniversityCourseSync";
import { useFeedbackPrompt } from "./useFeedbackPrompt";
import { useViewTransitionReset } from "./useViewTransitionReset";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";
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
  const [session, setSession] = useStoredLoginSession();
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
  const [panelMode, setPanelMode] = useState<LessonPanelMode | null>(null);
  const [canvasDocument, setCanvasDocument] = useState<CanvasDocument | null>(null);
  const [canvasError, setCanvasError] = useState<string | null>(null);
  const [focusedSectionId, setFocusedSectionId] = useState("bayesian-decision-theory-the-aim");
  const [highlightedBlockId, setHighlightedBlockId] = useState<string | null>(null);
  const [highlightedText, setHighlightedText] = useState<string | null>(null);
  const [navigationVersion, setNavigationVersion] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessagesForAttendance(lectures[2].attendance),
  );
  useVersionUpdateActivity(messages.some((message) => Boolean(message.isPending)));
  const [lastTutorModel, setLastTutorModel] = useState<string | null>(null);
  const [passedGateIds, setPassedGateIds] = useState<string[]>([]);
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
      const courses = await getCourses(activeSession);
      const demoCourse = readDemoWorkspaceCourse();
      const devCourse = developmentWorkspaceCourse();
      const preferredCourse = courses.find((course) => course.id === preferredCourseId);
      const storedCourses = [...courses].reverse();
      const candidates = [demoCourse, preferredCourse, devCourse, ...storedCourses].filter(
        (course, index, list): course is UniversityCourse =>
          Boolean(course) && list.findIndex((item) => item?.id === course?.id) === index,
      );
      for (const course of candidates) {
        const nextLectures = await getCourseLectures(course.id, activeSession);
        if (!nextLectures.length) continue;
        setWorkspaceCourse(course);
        setWorkspaceCourseId(course.id);
        setSelectedCourseId(course.id);
        setAvailableLectures(nextLectures);
        setSelectedLecture(
          (current) => nextLectures.find((lecture) => lecture.id === current.id) ?? nextLectures[0],
        );
        return;
      }
    } catch {
      setAvailableLectures(import.meta.env.DEV ? lectures : []);
    }
  }

  async function handleTutorMessage(message: string) {
    const timestamp = Date.now();
    const pendingMessageId = `agent-pending-${timestamp}`;
    setMessages((current) => [
      ...current,
      { id: `user-${timestamp}`, role: "user", content: message },
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
          canvas_state: { focused_section_id: focusedSectionId },
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
      setMessages((current) => current.filter((item) => item.id !== pendingMessageId));
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
    const passedGateId =
      result.quality_gate?.status === "passed" ? result.quality_gate.gate_id : null;
    if (passedGateId) {
      setPassedGateIds((current) =>
        current.includes(passedGateId) ? current : [...current, passedGateId],
      );
    }
    feedback.recordSuccessfulTutorTurn();
  }

  function handleLogout() {
    if (session) void logoutSession(session);
    setSession(null);
    clearSavedFlow();
    navigate(pathForView("login"), { replace: true });
    setPanelMode(null);
    setFocusedSectionId("bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setNavigationVersion((current) => current + 1);
    setCanvasDocument(null);
    setCanvasError(null);
    setMessages(initialMessagesForAttendance(lectures[2].attendance));
    setLastTutorModel(null);
    setPassedGateIds([]);
  }

  const handleOpenLecture = useCallback(
    async (
      courseId: string,
      lecture: Lecture,
      mode: LessonMode = "learner",
      updateRoute = true,
    ) => {
      loadedLessonRoute.current = lessonRouteKey(courseId, lecture.id, mode);
      if (updateRoute) navigate(lessonPath(courseId, lecture.id, mode));
      setSelectedCourseId(courseId);
      setSelectedLecture(lecture);
      setLessonMode(mode);
      setPanelMode(null);
      setCanvasDocument(null);
      setCanvasError(null);
      setFocusedSectionId("bayesian-decision-theory-the-aim");
      setHighlightedBlockId(null);
      setHighlightedText(null);
      setNavigationVersion((current) => current + 1);
      setMessages(initialMessagesForAttendance(lecture.attendance));
      setLastTutorModel(null);
      setPassedGateIds([]);

      try {
        const activeSession = session ?? localDemoSession;
        const document =
          mode === "draft" && session
            ? await getDraftLectureCanvas(courseId, lecture.id, session)
            : await getLectureCanvas(
                courseId,
                lecture.id,
                activeSession,
                mode === "professor-preview" ? "professor-preview" : "learner",
              );
        setCanvasDocument(document);
        setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
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
    const key = lessonRouteKey(route.courseId, route.lectureId, route.lessonMode);
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
    const document = await getLectureCanvas(
      selectedCourseId,
      selectedLecture.id,
      activeSession,
      workspaceMode,
    );
    setCanvasDocument(document);
    setCanvasError(null);
    setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setMessages(
      initialMessagesForAttendance(options.reset_progress ? "unknown" : selectedLecture.attendance),
    );
    setLastTutorModel(null);
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
        {courseManagerSession ? (
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
          passedGateIds={passedGateIds}
          publishedLectureIds={publishedLectureIds}
          selectedCourseId={selectedCourseId}
          selectedLecture={selectedLecture}
          route={route}
          session={session}
          view={view}
          workspaceCourse={workspaceCourse}
          workspaceCourseId={workspaceCourseId}
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
          onOpenLecture={(courseId, lecture) => {
            void handleOpenLecture(courseId, lecture);
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
          onResetWorkspace={handleResetWorkspace}
          onTogglePanel={(mode) => {
            setPanelMode((current) => (current === mode ? null : mode));
          }}
        />
        {view !== "lesson" ? (
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

function lessonRouteKey(courseId: string, lectureId: string, mode: LessonMode) {
  return `${mode}:${courseId}:${lectureId}`;
}
