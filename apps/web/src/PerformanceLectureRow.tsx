import { lectureSnapshot } from "./performanceMetrics";
import type { Lecture } from "./types";

export function PerformanceLectureRow({
  active,
  lecture,
  onSelect,
}: {
  active: boolean;
  lecture: Lecture;
  onSelect: () => void;
}) {
  const snapshot = lectureSnapshot(lecture, null);
  return (
    <button className={active ? "is-active" : undefined} type="button" onClick={onSelect}>
      <span className="lecture-index">{lecture.number}</span>
      <span className="lecture-row-body">
        <strong>{lecture.title}</strong>
        <small>{lecture.date}</small>
        <span className="lecture-row-metrics">
          <span>{snapshot.learners} learners</span>
          <span>{snapshot.quizRate} quiz</span>
          <span>{snapshot.gateRate} gates</span>
        </span>
      </span>
      <span className={`lecture-status is-${snapshot.status}`} />
    </button>
  );
}
