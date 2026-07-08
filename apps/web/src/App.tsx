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
import { AppHeader } from "./AppHeader";
import { initialMessagesForAttendance, localDemoSession, localProfessorSession } from "./appDefaults";
import { canManageCourses } from "./authz";
import { CourseManagementAccessRequired } from "./CourseManagementAccessRequired";
import { Dashboard } from "./Dashboard";
import { clearDemoWorkspaceCourse, readDemoWorkspaceCourse, writeDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { developmentWorkspaceCourse } from "./devWorkspaceAccess";
import { draftPreviewUrl } from "./draftPreviewUrl";
import { resetLearnerWorkspace } from "./learnerWorkspaceApi";
import { LessonWorkspace } from "./LessonWorkspace";
import { LoginView } from "./LoginView";
import { clearSavedFlow } from "./professorBuilderState";
import { useStoredLoginSession } from "./loginSessionStorage";
import { ProfileView } from "./ProfileView";
import { ProfessorCourseBuilder } from "./ProfessorCourseBuilder";
import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { lectures } from "./sampleData";
import { requestedTutorModel } from "./tutorModels";
import { useInitialDraftPreview } from "./useInitialDraftPreview";
import { usePublishedLectures } from "./usePublishedLectures";
import { useTutorModelPreference } from "./useTutorModelPreference";
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
  const [session, setSession] = useStoredLoginSession();
  const [view, setView] = useState<View>(session ? "dashboard" : "login");
  const [availableLectures, setAvailableLectures] = useState(lectures);
  const [workspaceCourse, setWorkspaceCourse] = useState<UniversityCourse>(localDemoSession.courses[0]);
  const [workspaceCourseId, setWorkspaceCourseId] = useState("martius-ml");
  const [selectedCourseId, setSelectedCourseId] = useState("martius-ml");
  const [selectedLecture, setSelectedLecture] = useState(lectures[2]);
  const [lessonUserId, setLessonUserId] = useState(effectiveUserId(session));
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
  const [tutorModelPreference, setTutorModelPreference] = useTutorModelPreference();
  const [publishedLectureIds, setPublishedLectureIds] = usePublishedLectures(
    workspaceCourseId,
    availableLectures,
    session,
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (!session) return;
    void loadWorkspaceCourse(session, workspaceCourseId);
  }, [session]);

  async function loadWorkspaceCourse(activeSession: LoginSession, preferredCourseId = workspaceCourseId) {
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
        setSelectedLecture((current) => nextLectures.find((lecture) => lecture.id === current.id) ?? nextLectures[0]);
        return;
      }
    } catch {
      setAvailableLectures(lectures);
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
      const requestedModel = requestedTutorModel(tutorModelPreference);
      result = await sendAgentTurnStream(
        {
          user_id: lessonUserId,
          course_id: selectedCourseId,
          lecture_id: selectedLecture.id,
          attendance: selectedLecture.attendance,
          message,
          ...(requestedModel ? { model: requestedModel } : {}),
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
    if (navigationTargetId && nextHighlightSectionId && nextHighlightSectionId !== navigationTargetId) {
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
  }

  function handleLogout() {
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
    setLessonUserId("local-demo");
    setLastTutorModel(null);
  }

  const handleOpenLecture = useCallback(async (
    courseId: string,
    lecture: Lecture,
    backView: "dashboard" | "professor" = "dashboard",
    userId = effectiveUserId(session),
    previewDraft = false,
  ) => {
    setSelectedCourseId(courseId);
    setSelectedLecture(lecture);
    setLessonUserId(userId);
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

    try {
      const activeSession = session ?? localDemoSession;
      const document = previewDraft && session
        ? await getDraftLectureCanvas(courseId, lecture.id, session)
        : await getLectureCanvas(courseId, lecture.id, userId, activeSession);
      setCanvasDocument(document);
      setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
    } catch (error) {
      setCanvasError(error instanceof Error ? error.message : "Canvas loading failed.");
    }
  }, [session]);

  useInitialDraftPreview({
    availableLectures,
    session,
    onBlocked: () => {
      setView("dashboard");
      setCanvasError("Draft preview requires a course-management account.");
    },
    onOpenLecture: (courseId, lecture, backView, userId, previewDraft) => {
      void handleOpenLecture(courseId, lecture, backView, userId, previewDraft);
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
      void loadWorkspaceCourse(session ?? localDemoSession, localDemoSession.courses[0].id);
    }
  }

  async function handleResetWorkspace(options: WorkspaceResetSelection) {
    const activeSession = session ?? localDemoSession;
    await resetLearnerWorkspace(
      selectedCourseId,
      { user_id: lessonUserId, ...options },
      activeSession,
    );
    if (options.reset_progress) {
      setAvailableLectures((current) => current.map((lecture) => ({ ...lecture, attendance: "unknown" })));
      setSelectedLecture((current) => ({ ...current, attendance: "unknown" }));
    }
    const document = await getLectureCanvas(selectedCourseId, selectedLecture.id, lessonUserId, activeSession);
    setCanvasDocument(document);
    setCanvasError(null);
    setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setMessages(initialMessagesForAttendance(options.reset_progress ? "unknown" : selectedLecture.attendance));
    setLastTutorModel(null);
    setNavigationVersion((current) => current + 1);
  }

  const courseManagerSession = canManageCourses(session) ? session : null;

  return (
    <div className="app-shell">
      <AppHeader
        activeView={view}
        session={session}
        theme={theme}
        onBrand={() => {
          setView(session ? "dashboard" : "login");
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

      {view === "login" ? (
        <LoginView
          onLogin={(nextSession) => {
            setSession(nextSession);
            setView("dashboard");
            void loadWorkspaceCourse(nextSession);
          }}
          onOpenDemo={() => {
            setSession(localDemoSession);
            setView("dashboard");
            void loadWorkspaceCourse(localDemoSession);
          }}
          onOpenProfessorDemo={() => {
            setSession(localProfessorSession);
            setView("professor");
            void loadWorkspaceCourse(localProfessorSession);
          }}
        />
      ) : view === "dashboard" ? (
        <Dashboard
          lectures={availableLectures}
          publishedLectureIds={publishedLectureIds}
          session={session}
          workspaceCourse={workspaceCourse}
          onOpen={(lecture) => {
            void handleOpenLecture(workspaceCourseId, lecture);
          }}
          onSetAttendance={handleSetAttendance}
        />
      ) : view === "profile" && session ? (
        <ProfileView
          modelPreference={tutorModelPreference}
          session={session}
          onBack={() => setView("dashboard")}
          onModelPreferenceChange={setTutorModelPreference}
        />
      ) : view === "professor" && courseManagerSession ? (
        <ProfessorCourseBuilder
          session={courseManagerSession}
          onPublishWorkspace={async (courseId, lectureId) => {
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
            setSelectedLecture((current) => nextLectures.find((lecture) => lecture.id === current.id) ?? nextLectures[0]);
            setPublishedLectureIds(nextLectures.map((lecture) => lecture.id));
          }}
          onWorkspaceDeleted={handleWorkspaceDeleted}
          previewWorkspaceUrl={draftPreviewUrl}
          publishedLectureIds={publishedLectureIds}
        />
      ) : view === "performance" && courseManagerSession ? (
        <ProfessorCoursePerformance
          lectures={availableLectures}
          publishedLectureIds={publishedLectureIds}
          session={courseManagerSession}
          workspaceCourse={workspaceCourse}
        />
      ) : view === "performance" ? (
        <CourseManagementAccessRequired
          label="Course performance"
          onBack={() => setView(session ? "dashboard" : "login")}
        />
      ) : view === "professor" ? (
        <CourseManagementAccessRequired
          label="Course management"
          onBack={() => setView(session ? "dashboard" : "login")}
        />
      ) : (
        <LessonWorkspace
          canvasDocument={canvasDocument}
          canvasError={canvasError}
          courseId={selectedCourseId}
          focusedSectionId={focusedSectionId}
          highlightedBlockId={highlightedBlockId}
          highlightedText={highlightedText}
          lecture={selectedLecture}
          messages={messages}
          session={session ?? localDemoSession}
          tutorModel={lastTutorModel ?? requestedTutorModel(tutorModelPreference)}
          navigationVersion={navigationVersion}
          panelMode={panelMode}
          userId={lessonUserId}
          backLabel={lessonBackView === "professor" ? "Course builder" : "Dashboard"}
          onBack={() => {
            setView(lessonBackView);
            setPanelMode(null);
          }}
          onSendMessage={handleTutorMessage}
          onResetWorkspace={handleResetWorkspace}
          onTogglePanel={(mode) => {
            setPanelMode((current) => (current === mode ? null : mode));
          }}
        />
      )}
    </div>
  );
}

function effectiveUserId(session: LoginSession | null) {
  return session?.username ?? "unknown-user";
}

export default App;
