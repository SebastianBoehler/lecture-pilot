import { X } from "lucide-react";
import { useState } from "react";

import { getExamReadinessCheck, submitExamReadinessAttempt } from "./api";
import { ExamReadinessResult } from "./ExamReadinessResult";
import type {
  ExamReadinessAnswer,
  ExamReadinessAttemptResult,
  ExamReadinessCheck,
  ExamReadinessQuestion,
  ExamReadinessQuestionResult,
  Lecture,
  LoginSession,
  UniversityCourse,
} from "./types";

type AnswerMap = Record<string, number | string>;

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
  const [check, setCheck] = useState<ExamReadinessCheck | null>(null);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [attemptResult, setAttemptResult] = useState<ExamReadinessAttemptResult | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const titleId = `exam-readiness-title-${course.id}`;

  async function startCheck() {
    if (!session) {
      setError("Sign in before starting the exam readiness check.");
      return;
    }
    setLoading(true);
    setError(null);
    setAttemptResult(null);
    setAnswers({});
    try {
      setCheck(await getExamReadinessCheck(course.id, session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Exam readiness check loading failed.");
    } finally {
      setLoading(false);
    }
  }

  function openCheck() {
    setOpen(true);
    if (!check && !loading) {
      void startCheck();
    }
  }

  async function submitCheck() {
    if (!check || !session) return;
    setSubmitting(true);
    setError(null);
    try {
      setAttemptResult(await submitExamReadinessAttempt(course.id, answersForCheck(check, answers), session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Exam readiness submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="exam-readiness" aria-label={`Prüfungs-ready check for ${course.title}`}>
      <header>
        <div>
          <h4>Prüfungs-ready check</h4>
          <p>10-question mixed sample across published lectures, with weak-topic revision links after submission.</p>
        </div>
        <div className="exam-readiness-actions">
          <button disabled={loading} type="button" onClick={openCheck}>
            {loading ? "Preparing check..." : check ? "Open check" : "Start exam check"}
          </button>
        </div>
      </header>
      {open ? (
        <div className="exam-modal-backdrop">
          <section
            aria-labelledby={titleId}
            aria-modal="true"
            className="exam-modal"
            role="dialog"
          >
            <header className="exam-modal-header">
              <div>
                <h2 id={titleId}>Prüfungs-ready check</h2>
                <p>Mixed exam practice across the published lectures in {course.title}.</p>
              </div>
              <div className="exam-modal-actions">
                <button disabled={loading} type="button" onClick={startCheck}>
                  {loading ? "Loading..." : "Restart sample"}
                </button>
                <button aria-label="Close exam readiness check" type="button" onClick={() => setOpen(false)}>
                  <X size={17} />
                </button>
              </div>
            </header>
            {error ? <p className="form-error">{error}</p> : null}
            {loading && !check ? <p className="drawer-note">Preparing your mixed lecture check...</p> : null}
            {check ? (
              <div className="exam-readiness-body">
                <p className="exam-readiness-meta">
                  {check.questions.length} sampled questions from {check.published_lecture_count} published lectures
                </p>
                {check.questions.map((question, index) => (
                  <QuestionField
                    answer={answers[question.id]}
                    index={index}
                    key={question.id}
                    question={question}
                    result={attemptResult?.results.find((item) => item.question_id === question.id)}
                    onAnswer={(answer) => setAnswers((current) => ({ ...current, [question.id]: answer }))}
                  />
                ))}
                <button
                  className="exam-submit"
                  disabled={!canSubmit(check, answers) || submitting || Boolean(attemptResult)}
                  type="button"
                  onClick={submitCheck}
                >
                  {submitting ? "Checking..." : "Check readiness"}
                </button>
                {attemptResult ? (
                  <ExamReadinessResult lectures={lectures} result={attemptResult} onOpenLecture={onOpenLecture} />
                ) : null}
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </section>
  );
}

function QuestionField({
  answer,
  index,
  onAnswer,
  question,
  result,
}: {
  answer: number | string | undefined;
  index: number;
  onAnswer: (answer: number | string) => void;
  question: ExamReadinessQuestion;
  result?: ExamReadinessQuestionResult;
}) {
  const submitted = Boolean(result);
  const correct = question.kind === "multiple_choice" && result?.status === "correct";
  return (
    <fieldset className={`exam-question${correct ? " is-correct" : ""}`}>
      <legend>
        <span>{String(index + 1).padStart(2, "0")}</span>
        {question.prompt}
      </legend>
      <small>{question.lecture_title} / {question.section_title}</small>
      {question.kind === "multiple_choice" ? (
        <div className="exam-options">
          {question.options.map((option, optionIndex) => (
            <label key={`${question.id}-${optionIndex}`}>
              <input
                checked={answer === optionIndex}
                disabled={submitted}
                name={question.id}
                type="radio"
                onChange={() => onAnswer(optionIndex)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          disabled={submitted}
          placeholder="Write a concise exam-style answer."
          value={typeof answer === "string" ? answer : ""}
          onChange={(event) => onAnswer(event.target.value)}
        />
      )}
      {result?.status === "needs_rubric_review" ? <p className="exam-review-status">Rubric review needed.</p> : null}
    </fieldset>
  );
}

function canSubmit(check: ExamReadinessCheck, answers: AnswerMap) {
  return check.questions.every((question) => {
    const answer = answers[question.id];
    return question.kind === "multiple_choice" ? typeof answer === "number" : String(answer ?? "").trim().length > 0;
  });
}

function answersForCheck(check: ExamReadinessCheck, answers: AnswerMap): ExamReadinessAnswer[] {
  return check.questions.map((question) => {
    const answer = answers[question.id];
    if (question.kind === "multiple_choice") {
      return { question_id: question.id, selected_index: Number(answer) };
    }
    return { question_id: question.id, text: String(answer ?? "").trim() };
  });
}
