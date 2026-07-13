import { Trash2 } from "lucide-react";

import { useI18n } from "./i18n";
import type { LectureScheduleItem } from "./types";

export function ProfessorLectureSchedule({
  disabled,
  isApplying,
  onApply,
  onChange,
  schedule,
}: {
  disabled: boolean;
  isApplying: boolean;
  onApply: () => void;
  onChange: (schedule: LectureScheduleItem[]) => void;
  schedule: LectureScheduleItem[];
}) {
  const { t } = useI18n();
  if (!schedule.length) return null;
  return (
    <section className="lecture-schedule" aria-label={t("builder.schedule.title")}>
      <header>
        <strong>{t("builder.schedule.title")}</strong>
        <span>
          {t(schedule.length === 1 ? "builder.schedule.helpOne" : "builder.schedule.help", {
            count: schedule.length,
          })}
        </span>
      </header>
      <div className="lecture-schedule-list">
        {schedule.map((lecture, index) => (
          <div className="lecture-schedule-row" key={`${lecture.number}-${index}`}>
            <div className="lecture-schedule-fields">
              <label>
                {t("builder.schedule.number")}
                <input
                  value={lecture.number}
                  onChange={(event) =>
                    onChange(updateSchedule(schedule, index, "number", event.target.value))
                  }
                />
              </label>
              <label>
                {t("builder.schedule.lectureTitle")}
                <input
                  value={lecture.title}
                  onChange={(event) =>
                    onChange(updateSchedule(schedule, index, "title", event.target.value))
                  }
                />
              </label>
              <label>
                {t("builder.schedule.date")}
                <input
                  placeholder="YYYY-MM-DD"
                  value={lecture.date}
                  onChange={(event) =>
                    onChange(updateSchedule(schedule, index, "date", event.target.value))
                  }
                />
              </label>
              <button
                aria-label={t("builder.schedule.remove", { number: lecture.number })}
                className="lecture-schedule-remove"
                disabled={disabled}
                type="button"
                onClick={() => {
                  if (
                    window.confirm(t("builder.schedule.removeConfirm", { title: lecture.title }))
                  ) {
                    onChange(schedule.filter((_, currentIndex) => currentIndex !== index));
                  }
                }}
              >
                <Trash2 aria-hidden="true" size={15} />
                {t("builder.schedule.removeLabel")}
              </button>
            </div>
            <small className="lecture-schedule-source" title={lecture.material_path ?? undefined}>
              {lecture.material_path ?? t("builder.schedule.noMatch")}
            </small>
          </div>
        ))}
      </div>
      <button className="primary-action" disabled={disabled} type="button" onClick={onApply}>
        {isApplying ? t("builder.schedule.applying") : t("builder.schedule.apply")}
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
  return schedule.map((lecture, currentIndex) =>
    currentIndex === index ? { ...lecture, [key]: value } : lecture,
  );
}
