import { useI18n } from "./i18n";
import type { ExamRevisionTask, Lecture } from "./types";

const initialPriorityCount = 3;

export function ExamReviewPlan({
  lectures,
  onOpenLecture,
  tasks,
}: {
  lectures: Lecture[];
  onOpenLecture: (lecture: Lecture) => void;
  tasks: ExamRevisionTask[];
}) {
  const { t } = useI18n();
  const initialTasks = tasks.slice(0, initialPriorityCount);
  const remainingTasks = tasks.slice(initialPriorityCount);

  return (
    <section className="exam-review-plan" aria-labelledby="exam-review-plan-title">
      <header>
        <div>
          <h4 id="exam-review-plan-title">{t("exam.review.title")}</h4>
        </div>
        <span>{t("exam.review.startWith")}</span>
      </header>
      <ol>{renderTasks(initialTasks, 0, tasks, lectures, onOpenLecture, t)}</ol>
      {remainingTasks.length ? (
        <details className="exam-review-more">
          <summary>
            {t(
              remainingTasks.length === 1
                ? "exam.review.showMore.one"
                : "exam.review.showMore.many",
              { count: remainingTasks.length },
            )}
          </summary>
          <ol>
            {renderTasks(remainingTasks, initialPriorityCount, tasks, lectures, onOpenLecture, t)}
          </ol>
        </details>
      ) : null}
    </section>
  );
}

function renderTasks(
  tasksToRender: ExamRevisionTask[],
  offset: number,
  allTasks: ExamRevisionTask[],
  lectures: Lecture[],
  onOpenLecture: (lecture: Lecture) => void,
  t: ReturnType<typeof useI18n>["t"],
) {
  return tasksToRender.map((task, localIndex) => {
    const index = localIndex + offset;
    const firstTaskForLecture =
      allTasks.findIndex((item) => item.lecture_id === task.lecture_id) === index;
    const lecture = firstTaskForLecture
      ? lectures.find((item) => item.id === task.lecture_id)
      : undefined;
    return (
      <li className="exam-review-item" key={task.id}>
        <span className="exam-priority-number" aria-hidden="true">
          {String(index + 1).padStart(2, "0")}
        </span>
        <div className="exam-review-copy">
          <h5>{task.section_title}</h5>
          <small>{task.lecture_title}</small>
          <p>{task.next_action}</p>
          <details>
            <summary>{t("exam.review.sourceDetail")}</summary>
            <div>
              <strong>{t("exam.review.evidence")}</strong>
              <p>{task.expected_evidence}</p>
              {task.source_ref ? <code>{task.source_ref}</code> : null}
            </div>
          </details>
        </div>
        {lecture ? (
          <button type="button" onClick={() => onOpenLecture(lecture)}>
            {t("exam.review.lecture", { number: lecture.number })}
          </button>
        ) : null}
      </li>
    );
  });
}
