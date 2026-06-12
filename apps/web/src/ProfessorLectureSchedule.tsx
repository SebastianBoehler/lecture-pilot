import type { LectureScheduleItem } from "./types";

export function ProfessorLectureSchedule({
  disabled,
  onApply,
  onChange,
  schedule,
}: {
  disabled: boolean;
  onApply: () => void;
  onChange: (schedule: LectureScheduleItem[]) => void;
  schedule: LectureScheduleItem[];
}) {
  if (!schedule.length) return null;
  return (
    <section className="lecture-schedule" aria-label="Proposed lecture schedule">
      <header>
        <strong>Proposed lecture schedule</strong>
        <span>{schedule.length} lectures inferred from the source bundle</span>
      </header>
      <div className="lecture-schedule-list">
        {schedule.map((lecture, index) => (
          <div className="lecture-schedule-row" key={`${lecture.number}-${index}`}>
            <label>
              No.
              <input
                value={lecture.number}
                onChange={(event) => onChange(updateSchedule(schedule, index, "number", event.target.value))}
              />
            </label>
            <label>
              Title
              <input
                value={lecture.title}
                onChange={(event) => onChange(updateSchedule(schedule, index, "title", event.target.value))}
              />
            </label>
            <label>
              Date
              <input
                placeholder="YYYY-MM-DD"
                value={lecture.date}
                onChange={(event) => onChange(updateSchedule(schedule, index, "date", event.target.value))}
              />
            </label>
            <small>{lecture.material_path ?? "No direct material match"}</small>
          </div>
        ))}
      </div>
      <button disabled={disabled} type="button" onClick={onApply}>
        Apply lecture schedule
      </button>
    </section>
  );
}

function updateSchedule(
  schedule: LectureScheduleItem[],
  index: number,
  key: "date" | "number" | "title",
  value: string,
) {
  return schedule.map((lecture, currentIndex) => (
    currentIndex === index ? { ...lecture, [key]: value } : lecture
  ));
}
