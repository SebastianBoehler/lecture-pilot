import { useCallback, useEffect, useState } from "react";

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
import { isDraftPreviewRequest, useInitialDraftPreview } from "./useInitialDraftPreview";
import { usePublishedLectures } from "./usePublishedLectures";
import type { WorkspaceResetSelection } from "./WorkspaceResetControl";
import type {
  Attendance,
  CanvasDocument,
  ChatMessage,
  LessonPanelMode,
  Lecture,
  LoginSession,
  Theme,
  UniversityCourse,
  View,
} from "./types";

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [locale, setLocale] = useState<Locale>(() => readLocalePreference());
  const [session, setSession] = useStoredLoginSession();
  const [view, setView] = useState<View>(() => landingView(session));
  const [availableLectures, setAvailableLectures] = useState(() =>
    import.meta.env.DEV ? lectures : [],
  );
  const [workspaceCourse, setWorkspaceCourse] = useState<UniversityCourse>(
    localDemoSession.courses[0],
  );
  const [workspaceCourseId, setWorkspaceCourseId] = useState(() =>
    import.meta.env.DEV ? "martius-ml" : "",
  );
  const [selectedCourseId, setSelectedCourseId] = useState(() =>
    import.meta.env.DEV ? "martius-ml" : "",
  );
  const [selectedLecture, setSelectedLecture] = useState(lectures[2]);
  const [lessonBackView, setLessonBackView] = useState<"dashboard" | "professor">("dashboard");
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
  const [lastTutorModel, setLastTutorModel] = useState<string | null>(null);
  const [passedGateIds, setPassedGateIds] = useState<string[]>([]);
  const [publishedLectureIds, setPublishedLectureIds] = usePublishedLectures(
    workspaceCourseId,
    availableLectures,
    session,
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = locale;
    writeLocalePreference(locale);
  }, [locale]);

  useEffect(() => {
    if (!session || isDraftPreviewRequest()) return;
    void loadWorkspaceCourse(session, workspaceCourseId);
  }, [session]);

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
  }

  function handleLogout() {
    if (session) void logoutSession(session);
    setSession(null);
    clearSavedFlow();
    setView("login");
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
      backView: "dashboard" | "professor" = "dashboard",
      previewDraft = false,
    ) => {
      setSelectedCourseId(courseId);
      setSelectedLecture(lecture);
      setLessonBackView(backView);
      setView("lesson");
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
          previewDraft && session
            ? await getDraftLectureCanvas(courseId, lecture.id, session)
            : await getLectureCanvas(courseId, lecture.id, activeSession);
        setCanvasDocument(document);
        setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
      } catch (error) {
        setCanvasError(error instanceof Error ? error.message : "Canvas loading failed.");
      }
    },
    [session],
  );

  useInitialDraftPreview({
    availableLectures,
    session,
    onBlocked: () => {
      setView("dashboard");
      setCanvasError("Draft preview requires a course-management account.");
    },
    onOpenLecture: (courseId, lecture, backView, previewDraft) => {
      void handleOpenLecture(courseId, lecture, backView, previewDraft);
    },
  });

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
    await resetLearnerWorkspace(selectedCourseId, options, activeSession);
    if (options.reset_progress) {
      setAvailableLectures((current) =>
        current.map((lecture) => ({ ...lecture, attendance: "unknown" })),
      );
      setSelectedLecture((current) => ({ ...current, attendance: "unknown" }));
    }
    const document = await getLectureCanvas(selectedCourseId, selectedLecture.id, activeSession);
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

  function changeView(nextView: View) {
    setView(nextView);
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
            setView(landingView(session));
            setPanelMode(null);
          }}
          onLogout={handleLogout}
          onOpenDashboard={() => {
            setView(session ? "dashboard" : "login");
            setPanelMode(null);
          }}
          onOpenPerformance={() => {
            if (courseManagerSession) {
              setView("performance");
              setPanelMode(null);
            }
          }}
          onOpenCourseManagement={() => {
            if (courseManagerSession) {
              setView("course-management");
              setPanelMode(null);
            }
          }}
          onOpenProfile={() => {
            setView("profile");
            setPanelMode(null);
          }}
          onOpenProfessor={() => {
            if (courseManagerSession) {
              setView("professor");
              setPanelMode(null);
            }
          }}
          onToggleTheme={() => setTheme(theme === "light" ? "dark" : "light")}
        />

        <AppRoutes
          availableLectures={availableLectures}
          canvasDocument={canvasDocument}
          canvasError={canvasError}
          courseManagerSession={courseManagerSession}
          focusedSectionId={focusedSectionId}
          highlightedBlockId={highlightedBlockId}
          highlightedText={highlightedText}
          lastTutorModel={lastTutorModel}
          lessonBackView={lessonBackView}
          messages={messages}
          navigationVersion={navigationVersion}
          panelMode={panelMode}
          passedGateIds={passedGateIds}
          publishedLectureIds={publishedLectureIds}
          selectedCourseId={selectedCourseId}
          selectedLecture={selectedLecture}
          session={session}
          view={view}
          workspaceCourse={workspaceCourse}
          workspaceCourseId={workspaceCourseId}
          onLogin={(nextSession) => {
            setSession(nextSession);
            changeView(landingView(nextSession));
            void loadWorkspaceCourse(nextSession);
          }}
          onSessionChange={setSession}
          onOpenDemo={() => {
            setSession(localDemoSession);
            changeView("dashboard");
            void loadWorkspaceCourse(localDemoSession);
          }}
          onOpenProfessorDemo={() => {
            setSession(localProfessorSession);
            changeView("professor");
            void loadWorkspaceCourse(localProfessorSession);
          }}
          onOpenLecture={(courseId, lecture) => {
            void handleOpenLecture(courseId, lecture);
          }}
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
            writeDemoWorkspaceCourse(course);
            setWorkspaceCourse(course);
            setWorkspaceCourseId(course.id);
            setSelectedCourseId(course.id);
            setAvailableLectures(nextLectures);
            setSelectedLecture(
              (current) =>
                nextLectures.find((lecture) => lecture.id === current.id) ?? nextLectures[0],
            );
            setPublishedLectureIds(nextLectures.map((lecture) => lecture.id));
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
            onOpenHowItWorks={() => setView("how-it-works")}
            onOpenLearningScience={() => setView("learning-science")}
            onOpenPrivacy={() => setView("privacy")}
          />
        ) : null}
      </div>
    </I18nProvider>
  );
}

export default App;

function landingView(session: LoginSession | null): View {
  if (!session) return "login";
  if ((session.account_type ?? "student") === "professor") {
    return canManageCourses(session) ? "professor" : "profile";
  }
  return "dashboard";
}
