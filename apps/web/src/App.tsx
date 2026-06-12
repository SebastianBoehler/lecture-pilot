import { useEffect, useRef, useState } from "react";

import { getDraftLectureCanvas, getLectureCanvas, publishLectureCanvas, sendAgentTurnStream } from "./api";
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
import { LessonWorkspace } from "./LessonWorkspace";
import { LoginView } from "./LoginView";
import { useStoredLoginSession } from "./loginSessionStorage";
import { ProfileView } from "./ProfileView";
import { ProfessorCourseBuilder } from "./ProfessorCourseBuilder";
import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { lectures } from "./sampleData";
import { usePublishedLectures } from "./usePublishedLectures";
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
  const [publishedLectureIds, setPublishedLectureIds] = usePublishedLectures("martius-ml", lectures, session);
  const initialDraftPreviewHandled = useRef(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (initialDraftPreviewHandled.current) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("preview") !== "draft") return;
    if (!session) return;
    initialDraftPreviewHandled.current = true;
    if (!canManageCourses(session)) {
      setView("dashboard");
      setCanvasError("Draft preview requires a course-management account.");
      return;
    }
    const courseId = params.get("courseId") ?? "martius-ml";
    const lectureId = params.get("lectureId") ?? "lecture-03";
    const lecture = availableLectures.find((item) => item.id === lectureId) ?? {
      id: lectureId,
      number: params.get("lectureNumber") ?? lectureId.replace("lecture-", ""),
      title: params.get("lectureTitle") ?? "Draft lecture",
      date: "Draft",
      attendance: "unknown" as Attendance,
    };
    void handleOpenLecture(courseId, lecture, "professor", "professor-preview", true);
  }, [availableLectures, session]);

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
    previewDraft = false,
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
      const activeSession = session ?? localDemoSession;
      const document = previewDraft && session
        ? await getDraftLectureCanvas(courseId, lecture.id, session)
        : await getLectureCanvas(courseId, lecture.id, userId, activeSession);
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

  function draftPreviewUrl(courseId: string, lecture: Lecture) {
    const params = new URLSearchParams({
      preview: "draft",
      courseId,
      lectureId: lecture.id,
      lectureNumber: lecture.number,
      lectureTitle: lecture.title,
    });
    return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
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
          }}
          onOpenDemo={() => {
            setSession(localDemoSession);
            setView("dashboard");
          }}
          onOpenProfessorDemo={() => {
            setSession(localProfessorSession);
            setView("professor");
          }}
        />
      ) : view === "dashboard" ? (
        <Dashboard
          lectures={availableLectures}
          publishedLectureIds={publishedLectureIds}
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
          onPublishWorkspace={async (courseId, lectureId) => {
            const result = await publishLectureCanvas(courseId, lectureId, courseManagerSession);
            setPublishedLectureIds((current) => Array.from(new Set([...current, lectureId])));
            return result;
          }}
          previewWorkspaceUrl={draftPreviewUrl}
          publishedLectureIds={publishedLectureIds}
        />
      ) : view === "performance" && courseManagerSession ? (
        <ProfessorCoursePerformance
          lectures={availableLectures}
          session={courseManagerSession}
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
