import { useEffect, useState } from "react";

import { getLectureCanvas, sendAgentTurnStream } from "./api";
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
import { useDemoTutorWorkspace } from "./demoTutorWorkspace";
import { LessonWorkspace } from "./LessonWorkspace";
import { LoginView } from "./LoginView";
import { useStoredLoginSession } from "./loginSessionStorage";
import { ProfileView } from "./ProfileView";
import { ProfessorCourseBuilder } from "./ProfessorCourseBuilder";
import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { lectures } from "./sampleData";
import type {
  Attendance,
  CanvasDocument,
  ChatMessage,
  LessonPanelMode,
  Lecture,
  LoginSession,
  Theme,
  View,
} from "./types";

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [session, setSession] = useStoredLoginSession();
  const [view, setView] = useState<View>(session ? "dashboard" : "login");
  const [availableLectures, setAvailableLectures] = useState(lectures);
  const [selectedCourseId, setSelectedCourseId] = useState("martius-ml");
  const [selectedLecture, setSelectedLecture] = useState(lectures[2]);
  const [lessonUserId, setLessonUserId] = useState(effectiveUserId(session));
  const [lessonBackView, setLessonBackView] = useState<"dashboard" | "professor">("dashboard");
  const [professorBackView, setProfessorBackView] = useState<"login" | "dashboard">(
    session ? "dashboard" : "login",
  );
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
  const [demoTutorPublished, publishDemoTutor, unpublishDemoTutor] = useDemoTutorWorkspace();

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

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
          user_id: lessonUserId,
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

    for (const command of result.canvas_commands) {
      const section = command.section;
      if ((command.type === "append_section" || command.type === "update_section") && section) {
        setCanvasDocument((current) => applyCanvasSection(current, section));
      }
      if (command.type === "focus_section" && command.section_id) {
        setFocusedSectionId(command.section_id);
        setNavigationVersion((current) => current + 1);
      }
      if (command.type === "highlight_span" && command.span_id) {
        setHighlightedBlockId(command.span_id);
        setHighlightedText(command.highlight_text ?? null);
        setNavigationVersion((current) => current + 1);
      }
    }

    setMessages((current) => completePendingTutorMessage(current, pendingMessageId, result));
  }

  function handleLogout() {
    setSession(null);
    setView("login");
    setPanelMode(null);
    setFocusedSectionId("bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setNavigationVersion((current) => current + 1);
    setCanvasDocument(null);
    setCanvasError(null);
    setMessages(initialMessagesForAttendance(lectures[2].attendance));
    setSelectedCourseId("martius-ml");
    setLessonUserId("local-demo");
    setLastTutorModel(null);
  }

  async function handleOpenLecture(
    courseId: string,
    lecture: Lecture,
    backView: "dashboard" | "professor" = "dashboard",
    userId = effectiveUserId(session),
  ) {
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
      const document = await getLectureCanvas(courseId, lecture.id, userId, session ?? localDemoSession);
      setCanvasDocument(document);
      setFocusedSectionId(document.sections[0]?.id ?? "bayesian-decision-theory-the-aim");
    } catch (error) {
      setCanvasError(error instanceof Error ? error.message : "Canvas loading failed.");
    }
  }

  function handleSetAttendance(lectureId: string, attendance: Attendance) {
    setAvailableLectures((current) =>
      current.map((lecture) => (lecture.id === lectureId ? { ...lecture, attendance } : lecture)),
    );
    if (selectedLecture.id === lectureId) {
      setSelectedLecture((current) => ({ ...current, attendance }));
    }
  }

  const courseManagerSession = canManageCourses(session) ? session : null;

  return (
    <div className="app-shell">
      <AppHeader
        session={session}
        theme={theme}
        onBrand={() => {
          setView(session ? "dashboard" : "login");
          setPanelMode(null);
        }}
        onLogout={handleLogout}
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
            setProfessorBackView("dashboard");
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
          }}
          onOpenDemo={() => {
            setSession(localDemoSession);
            setView("dashboard");
          }}
          onOpenProfessorDemo={() => {
            setSession(localProfessorSession);
            setProfessorBackView("dashboard");
            setView("professor");
          }}
        />
      ) : view === "dashboard" ? (
        <Dashboard
          lectures={availableLectures}
          tutorWorkspacePublished={demoTutorPublished}
          session={session}
          onOpen={(lecture) => {
            void handleOpenLecture("martius-ml", lecture);
          }}
          onSetAttendance={handleSetAttendance}
        />
      ) : view === "profile" && session ? (
        <ProfileView session={session} onBack={() => setView("dashboard")} />
      ) : view === "professor" && courseManagerSession ? (
        <ProfessorCourseBuilder
          session={courseManagerSession}
          onBack={() => setView(professorBackView)}
          onPublishWorkspace={publishDemoTutor}
          onResetWorkspace={unpublishDemoTutor}
          onPreviewWorkspace={(courseId, lecture) => {
            void handleOpenLecture(courseId, lecture, "professor", "professor-preview");
          }}
          workspacePublished={demoTutorPublished}
        />
      ) : view === "performance" && courseManagerSession ? (
        <ProfessorCoursePerformance
          lectures={availableLectures}
          session={courseManagerSession}
          onBack={() => setView("dashboard")}
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
          tutorModel={lastTutorModel}
          navigationVersion={navigationVersion}
          panelMode={panelMode}
          userId={lessonUserId}
          backLabel={lessonBackView === "professor" ? "Course builder" : "Dashboard"}
          onBack={() => {
            setView(lessonBackView);
            setPanelMode(null);
          }}
          onSendMessage={handleTutorMessage}
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
