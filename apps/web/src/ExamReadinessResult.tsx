import type { ExamReadinessAttemptResult, ExamRevisionTask, Lecture } from "./types";

export function ExamReadinessResult({
  lectures,
  onOpenLecture,
  result,
}: {
  lectures: Lecture[];
  onOpenLecture: (lecture: Lecture) => void;
  result: ExamReadinessAttemptResult;
}) {
  const ready = result.score !== null && result.score >= result.passing_score;
  const taskGroups = groupTasks(result.tasks);
  return (
    <section className={`exam-result${ready ? " is-ready" : ""}`}>
      <strong>{ready ? "Prüfungs-ready on scored checks" : "Keep reviewing"}</strong>
      <span>
        {result.score === null ? "Open-ended rubric review" : `${Math.round(result.score * 100)}% scored MC`}
        {" · "}
        {guidanceLabel(result.guidance_level)}
      </span>
      <p>
        {ready
          ? "MC answers are above the readiness threshold. Finish the rubric review tasks before relying on it."
          : "Work through the source-linked tasks, then rerun the check."}
      </p>
      <div className="exam-revision-list">
        {taskGroups.length ? (
          taskGroups.map((group) => {
            const lecture = lectures.find((item) => item.id === group.lectureId);
            return (
              <section className="exam-task-group" key={group.lectureId}>
                <header>
                  <strong>{group.lectureTitle}</strong>
                  {lecture ? (
                    <button type="button" onClick={() => onOpenLecture(lecture)}>
                      Review lecture {lecture.number}: {lecture.title}
                    </button>
                  ) : null}
                </header>
                {group.tasks.map((task) => (
                  <article className="exam-task" key={task.id}>
                    <small>{task.section_title}</small>
                    <p>{task.expected_evidence}</p>
                    <span>{task.next_action}</span>
                    {task.source_ref ? <code>{task.source_ref}</code> : null}
                  </article>
                ))}
              </section>
            );
          })
        ) : (
          <span>No revision tasks returned.</span>
        )}
      </div>
    </section>
  );
}

function groupTasks(tasks: ExamRevisionTask[]) {
  const groups = new Map<string, { lectureId: string; lectureTitle: string; tasks: ExamRevisionTask[] }>();
  for (const task of tasks) {
    const group = groups.get(task.lecture_id) ?? {
      lectureId: task.lecture_id,
      lectureTitle: task.lecture_title,
      tasks: [],
    };
    group.tasks.push(task);
    groups.set(task.lecture_id, group);
  }
  return Array.from(groups.values());
}

function guidanceLabel(level: ExamReadinessAttemptResult["guidance_level"]) {
  if (level === "challenge") return "challenge tasks";
  if (level === "scaffolded") return "scaffolded review";
  return "standard review";
}
