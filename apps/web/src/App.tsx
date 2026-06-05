import { BookOpen, ChevronLeft, FileText, Grid2X2, MessageSquare, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { sendAgentTurn, type CanvasCommand } from "./api";
import { LessonCanvas } from "./LessonCanvas";
import { lectures } from "./sampleData";
import { TutorDrawer } from "./TutorDrawer";
import type { CanvasSectionId, ChatMessage, Lecture, Theme, View } from "./types";

const initialMessages: ChatMessage[] = [
  {
    id: "agent-welcome",
    role: "agent",
    content: "I highlighted the definition that drives the proof. Want a short derivation check?",
  },
];

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<View>("dashboard");
  const [selectedLecture, setSelectedLecture] = useState(lectures[2]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [focusedSectionId, setFocusedSectionId] = useState<CanvasSectionId>("feature-maps");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

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
      user_id: "local-preview-user",
      course_id: "martius-ml",
      lecture_id: selectedLecture.id,
      attendance: selectedLecture.attendance,
      message,
      canvas_state: { focused_section_id: focusedSectionId },
    });

    for (const command of result.canvas_commands) {
      if (command.type === "focus_section" && isCanvasSection(command.section_id)) {
        setFocusedSectionId(command.section_id);
      }
    }

    setMessages((current) => [
      ...current,
      {
        id: `agent-${Date.now()}`,
        role: "agent",
        content: result.message,
        toolTags: toolTagsFromCommands(result.canvas_commands),
      },
    ]);
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <button
          className="brand"
          type="button"
          onClick={() => {
            setView("dashboard");
            setDrawerOpen(false);
          }}
        >
          <BookOpen size={18} />
          <span>LecturePilot</span>
        </button>
        <div className="top-status">
          <span>OpenRouter GLM 5.1</span>
          <span>Local workspace</span>
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

      {view === "dashboard" ? (
        <Dashboard
          lectures={lectures}
          onOpen={(lecture) => {
            setSelectedLecture(lecture);
            setView("lesson");
            setDrawerOpen(false);
            setFocusedSectionId("feature-maps");
            setMessages(initialMessages);
          }}
        />
      ) : (
        <LessonWorkspace
          drawerOpen={drawerOpen}
          focusedSectionId={focusedSectionId}
          lecture={selectedLecture}
          messages={messages}
          onBack={() => {
            setView("dashboard");
            setDrawerOpen(false);
          }}
          onSendMessage={handleTutorMessage}
          onToggleDrawer={() => setDrawerOpen((open) => !open)}
        />
      )}
    </div>
  );
}

function Dashboard({ lectures, onOpen }: { lectures: Lecture[]; onOpen: (lecture: Lecture) => void }) {
  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <p className="section-label">Sommer 2026</p>
        <h1>Grundlagen des Maschinellen Lernens</h1>
        <p>Prof. Georg Martius</p>
      </section>

      <section className="course-panel" aria-labelledby="available-lectures">
        <div className="panel-heading">
          <h2 id="available-lectures">Available lectures</h2>
          <span>Only past dates are shown</span>
        </div>
        <div className="lecture-list">
          {lectures.map((lecture) => (
            <article className="lecture-row" key={lecture.id}>
              <div className="lecture-number">{lecture.number}</div>
              <div>
                <h3>{lecture.title}</h3>
                <p>
                  {lecture.date} · attendance {lecture.attendance}
                </p>
              </div>
              <button type="button" onClick={() => onOpen(lecture)}>
                Open lecture {lecture.number}
              </button>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function LessonWorkspace({
  lecture,
  drawerOpen,
  focusedSectionId,
  messages,
  onBack,
  onSendMessage,
  onToggleDrawer,
}: {
  lecture: Lecture;
  drawerOpen: boolean;
  focusedSectionId: CanvasSectionId;
  messages: ChatMessage[];
  onBack: () => void;
  onSendMessage: (message: string) => Promise<void>;
  onToggleDrawer: () => void;
}) {
  const layoutClass = drawerOpen ? "lesson-layout drawer-open" : "lesson-layout";

  return (
    <main className={layoutClass}>
      <section className="lesson-main">
        <div className="lesson-toolbar">
          <button className="ghost-button" type="button" onClick={onBack}>
            <ChevronLeft size={17} />
            Dashboard
          </button>
          <span>{lecture.date}</span>
        </div>
        <LessonCanvas lecture={lecture} focusedSectionId={focusedSectionId} />
      </section>

      <aside className="rail" aria-label="Lesson controls">
        <button
          className="rail-button"
          type="button"
          aria-label={drawerOpen ? "Close tutor drawer" : "Open tutor drawer"}
          onClick={onToggleDrawer}
        >
          <MessageSquare size={18} />
        </button>
        <button className="rail-button" type="button" aria-label="Open artifacts">
          <Grid2X2 size={18} />
        </button>
        <button className="rail-button" type="button" aria-label="Open lecture notes">
          <FileText size={18} />
        </button>
      </aside>

      {drawerOpen ? <TutorDrawer messages={messages} onSendMessage={onSendMessage} /> : null}
    </main>
  );
}

function isCanvasSection(sectionId: string | null | undefined): sectionId is CanvasSectionId {
  return (
    sectionId === "learning-goals" ||
    sectionId === "feature-maps" ||
    sectionId === "kernel-trick" ||
    sectionId === "skill-check" ||
    sectionId === "failure-mode"
  );
}

function toolTagsFromCommands(commands: CanvasCommand[]): string[] {
  return commands.flatMap((command) => {
    if (command.type === "focus_section" && command.section_id) {
      return [`focus: ${command.section_id}`];
    }
    if (command.type === "open_artifact" && command.artifact_id) {
      return [`artifact: ${command.artifact_id}`];
    }
    if (command.type === "highlight_span" && command.span_id) {
      return [`highlight: ${command.span_id}`];
    }
    return [];
  });
}

export default App;
