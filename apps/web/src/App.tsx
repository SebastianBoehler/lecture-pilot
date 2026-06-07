import { LogOut, Moon, Sun, UserRound } from "lucide-react";
import { useEffect, useState } from "react";

import { getLectureCanvas, sendAgentTurn, type AgentTurnResult } from "./api";
import { initialMessages, localDemoSession } from "./appDefaults";
import { Dashboard } from "./Dashboard";
import { LessonWorkspace } from "./LessonWorkspace";
import { LoginView } from "./LoginView";
import { ProfileView } from "./ProfileView";
import { ProfessorCourseBuilder } from "./ProfessorCourseBuilder";
import { lectures } from "./sampleData";
import type {
  Attendance,
  CanvasDocument,
  CanvasSection,
  ChatMessage,
  LessonPanelMode,
  Lecture,
  LoginSession,
  Theme,
  View,
} from "./types";

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<View>("login");
  const [session, setSession] = useState<LoginSession | null>(null);
  const [availableLectures, setAvailableLectures] = useState(lectures);
  const [selectedLecture, setSelectedLecture] = useState(lectures[2]);
  const [panelMode, setPanelMode] = useState<LessonPanelMode | null>(null);
  const [canvasDocument, setCanvasDocument] = useState<CanvasDocument | null>(null);
  const [canvasError, setCanvasError] = useState<string | null>(null);
  const [focusedSectionId, setFocusedSectionId] = useState("bayesian-decision-theory-the-aim");
  const [highlightedBlockId, setHighlightedBlockId] = useState<string | null>(null);
  const [highlightedText, setHighlightedText] = useState<string | null>(null);
  const [navigationVersion, setNavigationVersion] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [lastTutorModel, setLastTutorModel] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const nextTheme = theme === "light" ? "dark" : "light";
  const themeLabel = `Switch to ${nextTheme} mode`;

  async function handleTutorMessage(message: string) {
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", content: message },
    ]);

    const result = await sendAgentTurn({
      user_id: effectiveUserId(session),
      course_id: "martius-ml",
      lecture_id: selectedLecture.id,
      attendance: selectedLecture.attendance,
      message,
      canvas_state: { focused_section_id: focusedSectionId },
    });
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

    setMessages((current) => [
      ...current,
      {
        id: `agent-${Date.now()}`,
        role: "agent",
        content: result.message,
        toolTags: toolTagsFromResult(result),
      },
    ]);
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
    setMessages(initialMessages);
    setLastTutorModel(null);
  }

  async function handleOpenLecture(lecture: Lecture) {
    setSelectedLecture(lecture);
    setView("lesson");
    setPanelMode(null);
    setCanvasDocument(null);
    setCanvasError(null);
    setFocusedSectionId("bayesian-decision-theory-the-aim");
    setHighlightedBlockId(null);
    setHighlightedText(null);
    setNavigationVersion((current) => current + 1);
    setMessages(initialMessages);
    setLastTutorModel(null);

    try {
      const document = await getLectureCanvas("martius-ml", lecture.id, effectiveUserId(session));
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

  return (
    <div className="app-shell">
      <header className="top-bar">
        <button
          className="brand"
          type="button"
          onClick={() => {
            setView(session ? "dashboard" : "login");
            setPanelMode(null);
          }}
        >
          <span>LecturePilot</span>
        </button>
        <div className="top-status">
          <span>Course workspace</span>
          {session ? (
            <div className="top-actions" aria-label="Account controls">
              <button
                className="top-action-button"
                type="button"
                aria-label="Open profile"
                onClick={() => {
                  setView("profile");
                  setPanelMode(null);
                }}
              >
                <UserRound size={16} />
                <span>Profile</span>
              </button>
              <button
                className="top-action-button"
                type="button"
                aria-label="Log out"
                onClick={handleLogout}
              >
                <LogOut size={16} />
                <span>Log out</span>
              </button>
            </div>
          ) : null}
          <button
            className="icon-button"
            type="button"
            aria-label={themeLabel}
            onClick={() => setTheme(nextTheme)}
          >
            {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
          </button>
        </div>
      </header>

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
          onOpenProfessor={() => {
            setSession(null);
            setView("professor");
          }}
        />
      ) : view === "dashboard" ? (
        <Dashboard
          lectures={availableLectures}
          session={session}
          onOpen={handleOpenLecture}
          onSetAttendance={handleSetAttendance}
        />
      ) : view === "profile" && session ? (
        <ProfileView session={session} onBack={() => setView("dashboard")} />
      ) : view === "professor" ? (
        <ProfessorCourseBuilder onBack={() => setView("login")} />
      ) : (
        <LessonWorkspace
          canvasDocument={canvasDocument}
          canvasError={canvasError}
          focusedSectionId={focusedSectionId}
          highlightedBlockId={highlightedBlockId}
          highlightedText={highlightedText}
          lecture={selectedLecture}
          messages={messages}
          tutorModel={lastTutorModel}
          navigationVersion={navigationVersion}
          panelMode={panelMode}
          onBack={() => {
            setView("dashboard");
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

function applyCanvasSection(document: CanvasDocument | null, section: CanvasSection) {
  if (!document) {
    return document;
  }
  const sectionIndex = document.sections.findIndex((candidate) => candidate.id === section.id);
  if (sectionIndex === -1) {
    return { ...document, sections: [...document.sections, section] };
  }
  const sections = [...document.sections];
  sections[sectionIndex] = section;
  return { ...document, sections };
}

function toolTagsFromResult(result: AgentTurnResult): string[] {
  const commandTags = result.canvas_commands.flatMap((command) => {
    if (command.type === "focus_section" && command.section_id) {
      return [`focus: ${command.section_id}`];
    }
    if (command.type === "open_artifact" && command.artifact_id) {
      return [`artifact: ${command.artifact_id}`];
    }
    if (command.type === "highlight_span" && command.span_id) {
      return command.highlight_text
        ? [`highlight: ${command.span_id}`, `phrase: ${command.highlight_text}`]
        : [`highlight: ${command.span_id}`];
    }
    if ((command.type === "append_section" || command.type === "update_section") && command.section_id) {
      return [`canvas: ${command.section_id}`];
    }
    return [];
  });
  const gateTags = result.quality_gate
    ? [`gate: ${result.quality_gate.status.replace("_", " ")}`]
    : [];
  return [...commandTags, ...gateTags];
}

function effectiveUserId(session: LoginSession | null) {
  return session?.username ?? "unknown-user";
}

export default App;
