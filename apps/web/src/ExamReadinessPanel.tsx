import { useRef, useState } from "react";

import { getExamReadinessCheck, submitExamReadinessAttempt } from "./api";
import { answersForCheck } from "./examReadinessState";
import type { ExamAnswerMap } from "./examReadinessState";
import { ExamReadinessModal } from "./ExamReadinessModal";
import { useI18n } from "./i18n";
import type {
  ExamReadinessAttemptResult,
  ExamReadinessCheck,
  Lecture,
  LoginSession,
  UniversityCourse,
} from "./types";

export function ExamReadinessPanel({
  course,
  lectures,
  onOpenLecture,
  session,
}: {
  course: UniversityCourse;
  lectures: Lecture[];
  onOpenLecture: (lecture: Lecture) => void;
  session: LoginSession | null;
}) {
  const { t } = useI18n();
  const [check, setCheck] = useState<ExamReadinessCheck | null>(null);
  const [answers, setAnswers] = useState<ExamAnswerMap>({});
  const [attemptResult, setAttemptResult] = useState<ExamReadinessAttemptResult | null>(null);
  const [activeQuestion, setActiveQuestion] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  async function startCheck() {
    if (!session) {
      setError(t("exam.signInRequired"));
      return;
    }
    setLoading(true);
    setError(null);
    setCheck(null);
    setAttemptResult(null);
    setAnswers({});
    setActiveQuestion(0);
    try {
      setCheck(await getExamReadinessCheck(course.id, session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("exam.loadFailed"));
    } finally {
      setLoading(false);
    }
  }

  function openCheck() {
    setOpen(true);
    if (!check && !loading) void startCheck();
  }

  function closeCheck() {
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }

  async function submitCheck() {
    if (!check || !session) return;
    setSubmitting(true);
    setError(null);
    try {
      setAttemptResult(
        await submitExamReadinessAttempt(course.id, answersForCheck(check, answers), session),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("exam.submitFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      className="exam-readiness"
      aria-label={t("exam.panel.label", { course: course.title })}
    >
      <header>
        <div>
          <h4>{t("exam.title")}</h4>
          <p>{t("exam.panel.help")}</p>
        </div>
        <div className="exam-readiness-actions">
          <button ref={triggerRef} disabled={loading} type="button" onClick={openCheck}>
            {loading ? t("exam.preparing") : check ? t("exam.open") : t("exam.start")}
          </button>
        </div>
      </header>
      {open ? (
        <ExamReadinessModal
          activeQuestion={activeQuestion}
          answers={answers}
          check={check}
          course={course}
          error={error}
          lectures={lectures}
          loading={loading}
          result={attemptResult}
          submitting={submitting}
          onAnswer={(question, answer) =>
            setAnswers((current) => ({ ...current, [question.id]: answer }))
          }
          onBack={() => setActiveQuestion((current) => Math.max(0, current - 1))}
          onClose={closeCheck}
          onNext={() =>
            setActiveQuestion((current) =>
              Math.min((check?.questions.length ?? 1) - 1, current + 1),
            )
          }
          onOpenLecture={onOpenLecture}
          onRestart={() => void startCheck()}
          onSubmit={() => void submitCheck()}
        />
      ) : null}
    </section>
  );
}
