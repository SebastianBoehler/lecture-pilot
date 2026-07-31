import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import {
  deletePracticeExam,
  generatePracticeExam,
  listPpiExamSources,
  listPracticeExams,
  practiceExamGenerationStatus,
} from "./practiceExamApi";
import { clearPracticeExamDraft, ensurePracticeExamDraftAccount } from "./practiceExamDraft";
import { PracticeExamSetup } from "./PracticeExamSetup";
import type { PpiExamSource, PracticeExam, PracticeExamGenerationInput } from "./practiceExamTypes";
import { PracticeExamView } from "./PracticeExamView";
import type { LoginSession, UniversityCourse } from "./types";

export function PracticeExamPanel({
  course,
  session,
}: {
  course: UniversityCourse;
  session: LoginSession | null;
}) {
  const { t } = useI18n();
  const [exams, setExams] = useState<PracticeExam[]>([]);
  const [sources, setSources] = useState<PpiExamSource[]>([]);
  const [setupOpen, setSetupOpen] = useState(false);
  const [activeExam, setActiveExam] = useState<PracticeExam | null>(null);
  const [generationKey, setGenerationKey] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    ensurePracticeExamDraftAccount(session.username);
    let active = true;
    void Promise.all([
      listPracticeExams(course.id, session),
      listPpiExamSources(course.id, session),
    ])
      .then(([nextExams, nextSources]) => {
        if (!active) return;
        setExams(nextExams);
        setSources(nextSources);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : t("practice.loadFailed"));
      });
    return () => {
      active = false;
    };
  }, [course.id, session, t]);

  function openSetup() {
    if (!session) {
      setError(t("practice.signInRequired"));
      return;
    }
    setGenerationKey(crypto.randomUUID());
    setError(null);
    setSetupOpen(true);
  }

  async function generate(input: PracticeExamGenerationInput) {
    if (!session || !generationKey) return;
    setGenerating(true);
    setError(null);
    try {
      const exam = await generatePracticeExam(course.id, input, generationKey, session);
      setExams((current) => [exam, ...current.filter((item) => item.id !== exam.id)]);
      setSetupOpen(false);
      setActiveExam(exam);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : t("practice.generateFailed");
      let retainGenerationKey = false;
      if (message.includes("still running")) {
        try {
          const status = await practiceExamGenerationStatus(course.id, generationKey, session);
          if (status.status === "completed") {
            const refreshed = await listPracticeExams(course.id, session);
            const exam = refreshed.find((item) => item.id === status.exam_id);
            if (exam) {
              setExams(refreshed);
              setSetupOpen(false);
              setActiveExam(exam);
              return;
            }
          }
          retainGenerationKey = status.status === "running";
        } catch {
          retainGenerationKey = true;
        }
      }
      if (!retainGenerationKey) setGenerationKey(crypto.randomUUID());
      setError(message);
    } finally {
      setGenerating(false);
    }
  }

  async function remove(exam: PracticeExam) {
    if (!session || !window.confirm(t("practice.deleteConfirm"))) return;
    try {
      await deletePracticeExam(course.id, exam.id, session);
      clearPracticeExamDraft(session.username, course.id, exam.id);
      setExams((current) => current.filter((item) => item.id !== exam.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.deleteFailed"));
    }
  }

  return (
    <section
      className="practice-exams"
      aria-label={t("practice.panelLabel", { course: course.title })}
    >
      <header>
        <div>
          <h4>{t("practice.title")}</h4>
          <p>{t("practice.help")}</p>
        </div>
        <button type="button" onClick={openSetup}>
          {t("practice.generate")}
        </button>
      </header>
      {error && !setupOpen ? (
        <p className="practice-exam-error" role="alert">
          {error}
        </p>
      ) : null}
      {exams.length ? (
        <ul className="practice-exam-library">
          {exams.map((exam) => (
            <li key={exam.id}>
              <div>
                <strong>{exam.title}</strong>
                <span>
                  {t("practice.examMeta", {
                    count: exam.questions.length,
                    minutes: exam.duration_minutes,
                  })}
                </span>
              </div>
              <div>
                <button type="button" onClick={() => setActiveExam(exam)}>
                  {t("practice.openOnline")}
                </button>
                <button type="button" onClick={() => void remove(exam)}>
                  {t("practice.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="practice-empty-copy">{t("practice.empty")}</p>
      )}
      {setupOpen && session ? (
        <PracticeExamSetup
          course={course}
          error={error}
          generating={generating}
          session={session}
          sources={sources}
          onClose={() => setSetupOpen(false)}
          onGenerate={(input) => void generate(input)}
          onSourceImported={(source) =>
            setSources((current) => [source, ...current.filter((item) => item.id !== source.id)])
          }
        />
      ) : null}
      {activeExam && session ? (
        <PracticeExamView
          courseId={course.id}
          exam={activeExam}
          session={session}
          onClose={() => setActiveExam(null)}
        />
      ) : null}
    </section>
  );
}
