import { MathText } from "./MathText";
import { useI18n } from "./i18n";
import { choiceResult } from "./practiceExamScoring";
import type {
  PracticeExam,
  PracticeExamAnswers,
  PracticeExamAnswer,
  PracticeExamSolutionQuestion,
  PracticeExamSolutionSheet as SolutionSheet,
} from "./practiceExamTypes";

export function PracticeExamSolutionSheet({
  answers,
  exam,
  solutions,
}: {
  answers: PracticeExamAnswers;
  exam: PracticeExam;
  solutions: SolutionSheet;
}) {
  const { t } = useI18n();
  const score = multipleChoiceScore(answers, solutions);
  return (
    <section className="practice-solution-sheet" aria-labelledby="practice-solution-title">
      <div className="practice-solution-summary">
        <div>
          <p>{t("practice.solutions.eyebrow")}</p>
          <h3 id="practice-solution-title">{t("practice.solutions.title")}</h3>
        </div>
        <strong>
          {t("practice.solutions.score", {
            earned: score.earnedPoints,
            available: score.availablePoints,
          })}
        </strong>
        <span>
          {t("practice.solutions.correctCount", {
            correct: score.correctCount,
            total: score.questionCount,
          })}
        </span>
      </div>
      <p className="practice-solution-note">{t("practice.solutions.openHelp")}</p>
      {solutions.questions.some((q) => q.kind === "multiple_select") ? (
        <p>{t("practice.multipleRule")}</p>
      ) : null}
      <ol className="practice-solution-list">
        {solutions.questions.map((solution, index) => {
          const question = exam.questions.find((item) => item.id === solution.id);
          if (!question) return null;
          const answer = answers[question.id];
          return (
            <li key={solution.id}>
              <header>
                <span>{t("practice.question", { number: index + 1 })}</span>
                <strong>{t("practice.points", { count: solution.points })}</strong>
              </header>
              <div className="practice-solution-prompt">
                <MathText highlightedText={null} text={question.prompt} />
              </div>
              {solution.status === "invalid" ? null : solution.kind === "multiple_choice" ||
                solution.kind === "multiple_select" ? (
                <MultipleChoiceSolution
                  solution={solution}
                  options={question.options}
                  answer={answer}
                />
              ) : (
                <OpenAnswerSolution
                  referenceAnswer={solution.reference_answer}
                  rubric={solution.rubric}
                  studentAnswer={answer?.text}
                />
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function MultipleChoiceSolution({
  solution,
  options,
  answer,
}: {
  solution: PracticeExamSolutionQuestion;
  options: string[];
  answer?: PracticeExamAnswer;
}) {
  const { t } = useI18n();
  const result = choiceResult(solution, answer);
  const status = result.unanswered ? "unanswered" : result.correct ? "correct" : "incorrect";
  return (
    <div className="practice-solution-detail">
      <strong className={`practice-solution-status is-${status}`}>
        {t(`practice.solutions.${status}`)}
      </strong>
      <span>
        {t("practice.solutions.questionScore", {
          earned: result.points,
          available: solution.points,
        })}
      </span>
      <SolutionValue
        label={t("practice.solutions.yourAnswer")}
        value={result.selected.map((i) => options[i]).join("; ") || null}
      />
      <SolutionValue
        label={t("practice.solutions.correctAnswer")}
        value={result.keys.map((i) => options[i]).join("; ") || null}
      />
    </div>
  );
}

function OpenAnswerSolution({
  referenceAnswer,
  rubric,
  studentAnswer,
}: {
  referenceAnswer: string | null;
  rubric: string[];
  studentAnswer?: string;
}) {
  const { t } = useI18n();
  return (
    <div className="practice-solution-detail">
      <SolutionValue label={t("practice.solutions.yourAnswer")} value={studentAnswer} />
      <SolutionValue label={t("practice.solutions.referenceAnswer")} value={referenceAnswer} />
      <div>
        <strong>{t("practice.solutions.rubric")}</strong>
        <ul>
          {rubric.map((criterion) => (
            <li key={criterion}>
              <MathText highlightedText={null} text={criterion} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function SolutionValue({ label, value }: { label: string; value?: string | null }) {
  const { t } = useI18n();
  return (
    <div>
      <strong>{label}</strong>
      {value ? (
        <div>
          <MathText highlightedText={null} text={value} />
        </div>
      ) : (
        <p>{t("practice.solutions.noAnswer")}</p>
      )}
    </div>
  );
}

function multipleChoiceScore(answers: PracticeExamAnswers, solutions: SolutionSheet) {
  const questions = solutions.questions.filter(
    (question) => question.status !== "invalid" && question.kind !== "open_ended",
  );
  return questions.reduce(
    (score, question) => {
      const result = choiceResult(question, answers[question.id]);
      if (result.correct) {
        score.correctCount += 1;
      }
      score.earnedPoints += result.points;
      score.availablePoints += question.points;
      return score;
    },
    { availablePoints: 0, correctCount: 0, earnedPoints: 0, questionCount: questions.length },
  );
}
