import { lazy, Suspense, useState } from "react";

import { useI18n } from "./i18n";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

const ExamReadinessPanel = lazy(() =>
  import("./ExamReadinessPanel").then((module) => ({ default: module.ExamReadinessPanel })),
);
const PracticeExamPanel = lazy(() =>
  import("./PracticeExamPanel").then((module) => ({ default: module.PracticeExamPanel })),
);

export type ExamPrepMode = "quick" | "mock";

const MODES: ExamPrepMode[] = ["quick", "mock"];

/** One exam-prep tab with two modes; each mode keeps its own backend and loads on first use. */
export function ExamPrepPanel({
  course,
  lectures,
  session,
  onOpenLecture,
  onProgress,
}: {
  course: UniversityCourse;
  lectures: Lecture[];
  session: LoginSession | null;
  onOpenLecture: (lecture: Lecture) => void;
  onProgress: () => void | Promise<void>;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<ExamPrepMode>("quick");
  const [opened, setOpened] = useState<ExamPrepMode[]>(["quick"]);

  function select(next: ExamPrepMode) {
    setMode(next);
    setOpened((current) => (current.includes(next) ? current : [...current, next]));
  }

  return (
    <div className="exam-prep">
      <div aria-label={t("examPrep.modes")} className="exam-prep-modes" role="group">
        {MODES.map((item) => (
          <button
            aria-pressed={mode === item}
            className={mode === item ? "is-active" : undefined}
            key={item}
            type="button"
            onClick={() => select(item)}
          >
            <strong>{t(`examPrep.${item}.title`)}</strong>
            <span>{t(`examPrep.${item}.help`)}</span>
          </button>
        ))}
      </div>
      {opened.includes("quick") ? (
        <div hidden={mode !== "quick"}>
          <Suspense fallback={<p role="status">{t("app.loadingView")}</p>}>
            <ExamReadinessPanel
              course={course}
              lectures={lectures}
              session={session}
              onOpenLecture={onOpenLecture}
              onProgress={onProgress}
            />
          </Suspense>
        </div>
      ) : null}
      {opened.includes("mock") ? (
        <div hidden={mode !== "mock"}>
          <Suspense fallback={<p role="status">{t("app.loadingView")}</p>}>
            <PracticeExamPanel course={course} session={session} />
          </Suspense>
        </div>
      ) : null}
    </div>
  );
}
