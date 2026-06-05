import { BookOpen, ChevronLeft, FileText, Grid2X2, MessageSquare, Moon, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type Theme = "light" | "dark";
type View = "dashboard" | "lesson";

type Lecture = {
  id: string;
  number: string;
  title: string;
  date: string;
  attendance: "unknown" | "present" | "absent";
};

const lectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Introduction and Learning Setup",
    date: "May 6",
    attendance: "present",
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Linear Models and Generalization",
    date: "May 13",
    attendance: "unknown",
  },
  {
    id: "lecture-03",
    number: "03",
    title: "Kernels and Feature Maps",
    date: "Jun 4",
    attendance: "absent",
  },
];

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<View>("dashboard");
  const [selectedLecture, setSelectedLecture] = useState(lectures[2]);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const nextTheme = theme === "light" ? "dark" : "light";
  const themeLabel = `Switch to ${nextTheme} mode`;

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
          }}
        />
      ) : (
        <LessonWorkspace
          lecture={selectedLecture}
          drawerOpen={drawerOpen}
          onBack={() => {
            setView("dashboard");
            setDrawerOpen(false);
          }}
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
  onBack,
  onToggleDrawer,
}: {
  lecture: Lecture;
  drawerOpen: boolean;
  onBack: () => void;
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
        <LessonCanvas lecture={lecture} />
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

      {drawerOpen ? <TutorDrawer /> : null}
    </main>
  );
}

function LessonCanvas({ lecture }: { lecture: Lecture }) {
  return (
    <article className="canvas">
      <p className="section-label">Lecture {lecture.number}</p>
      <h1>{lecture.title}</h1>
      <p className="lead">
        The official notes introduce a feature map view first, then use it to motivate kernels as
        inner products in a lifted space.
      </p>
      <section className="canvas-section">
        <h2>Feature maps</h2>
        <p>
          A feature map <code>phi(x)</code> transforms input data into a representation where simple
          linear methods can express richer decision boundaries.
        </p>
        <p className="highlighted">
          The key argument is that the learning algorithm only needs inner products between mapped
          examples, not the explicit coordinates of the mapped vectors.
        </p>
      </section>
      <section className="canvas-section">
        <h2>Kernel trick</h2>
        <p>
          A kernel function computes <code>k(x, x')</code> directly, matching the inner product in
          feature space while avoiding an expensive explicit expansion.
        </p>
      </section>
    </article>
  );
}

function TutorDrawer() {
  const tabs = useMemo(() => ["Summary", "Quiz", "Code", "Diagram"], []);

  return (
    <aside className="drawer" aria-label="Tutor drawer">
      <div className="drawer-section">
        <h2>Tutor</h2>
        <div className="chat-message agent">
          I highlighted the definition that drives the proof. Want a short derivation check?
        </div>
        <textarea placeholder="Ask about this lecture..." rows={4} />
      </div>
      <div className="artifact-tabs" role="tablist" aria-label="Artifacts">
        {tabs.map((tab) => (
          <button role="tab" type="button" key={tab}>
            {tab}
          </button>
        ))}
      </div>
      <div className="artifact-card">
        <h3>Quiz: Feature Maps</h3>
        <p>Which part of the kernel trick avoids explicitly constructing feature vectors?</p>
      </div>
    </aside>
  );
}

export default App;

