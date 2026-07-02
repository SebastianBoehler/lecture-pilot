import { useState } from "react";

import { getExamReadinessCheck } from "./api";
import type { ExamReadinessCheck, ExamReadinessQuestion, Lecture, LoginSession, UniversityCourse } from "./types";

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
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const result = check && submitted ? gradeCheck(check, answers) : null;

  async function startCheck() {
    if (!session) {
      setError("Sign in before starting the exam readiness check.");
      return;
    }
    setLoading(true);
    setError(null);
    setSubmitted(false);
    setAnswers({});
    try {
      setCheck(await getExamReadinessCheck(course.id, session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Exam readiness check loading failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="exam-readiness" aria-label={`Prüfungs-ready check for ${course.title}`}>
      <header>
        <div>
          <h4>Prüfungs-ready check</h4>
          <p>Mixed questions across published lectures, with weak-topic revision links after submission.</p>
        </div>
        <button disabled={loading} type="button" onClick={startCheck}>
          {loading ? "Loading check..." : check ? "Restart check" : "Start check"}
        </button>
      </header>
      {error ? <p className="form-error">{error}</p> : null}
      {check ? (
        <div className="exam-readiness-body">
          <p className="exam-readiness-meta">
            {check.questions.length} questions from {check.published_lecture_count} published lectures
          </p>
          {check.questions.map((question, index) => (
            <QuestionField
              answer={answers[question.id]}
              index={index}
              key={question.id}
              question={question}
              submitted={submitted}
              onAnswer={(answer) => setAnswers((current) => ({ ...current, [question.id]: answer }))}
            />
          ))}
          <button
            className="exam-submit"
            disabled={!canSubmit(check, answers)}
            type="button"
            onClick={() => setSubmitted(true)}
          >
            Check readiness
          </button>
          {result ? (
            <ReadinessResult
              check={check}
              lectures={lectures}
              result={result}
              onOpenLecture={onOpenLecture}
            />
          ) : null}
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
  submitted,
}: {
  answer: number | string | undefined;
  index: number;
  onAnswer: (answer: number | string) => void;
  question: ExamReadinessQuestion;
  submitted: boolean;
}) {
  const correct = question.kind === "multiple_choice" && submitted && answer === question.answer_index;
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
      {submitted ? <Rubric question={question} /> : null}
    </fieldset>
  );
}

function Rubric({ question }: { question: ExamReadinessQuestion }) {
  if (!question.rubric.length) return null;
  return (
    <ul className="exam-rubric">
      {question.rubric.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function ReadinessResult({
  check,
  lectures,
  onOpenLecture,
  result,
}: {
  check: ExamReadinessCheck;
  lectures: Lecture[];
  onOpenLecture: (lecture: Lecture) => void;
  result: ReturnType<typeof gradeCheck>;
}) {
  const ready = result.score !== null && result.score >= check.passing_score;
  const weakLectureIds = result.weakLectureIds.length ? result.weakLectureIds : check.coverage.map((item) => item.lecture_id);
  return (
    <section className={`exam-result${ready ? " is-ready" : ""}`}>
      <strong>{ready ? "Prüfungs-ready" : "Keep reviewing"}</strong>
      <span>{result.score === null ? "Open-ended review mode" : `${Math.round(result.score * 100)}% scored MC`}</span>
      <p>{ready ? "MC answers are above the readiness threshold." : "Review weak topics, then rerun the check."}</p>
      <div className="exam-revision-list">
        {weakLectureIds.map((lectureId) => {
          const lecture = lectures.find((item) => item.id === lectureId);
          if (!lecture) return null;
          return (
            <button key={lecture.id} type="button" onClick={() => onOpenLecture(lecture)}>
              Review lecture {lecture.number}: {lecture.title}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function canSubmit(check: ExamReadinessCheck, answers: AnswerMap) {
  return check.questions.every((question) => {
    const answer = answers[question.id];
    return question.kind === "multiple_choice" ? typeof answer === "number" : String(answer ?? "").trim().length > 0;
  });
}

function gradeCheck(check: ExamReadinessCheck, answers: AnswerMap) {
  const scored = check.questions.filter((question) => question.kind === "multiple_choice");
  const wrong = scored.filter((question) => answers[question.id] !== question.answer_index);
  return {
    score: scored.length ? (scored.length - wrong.length) / scored.length : null,
    weakLectureIds: Array.from(new Set(wrong.map((question) => question.lecture_id))),
  };
}
