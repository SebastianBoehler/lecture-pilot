import { useState } from "react";
import { ArrowDown, ArrowUp, GripVertical, Trash2 } from "lucide-react";

import { useI18n } from "./i18n";
import { reorderLectureSchedule } from "./lectureScheduleReorder";
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
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  const moveLecture = (fromIndex: number, toIndex: number) =>
    onChange(reorderLectureSchedule(schedule, fromIndex, toIndex));
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
        <p className="lecture-schedule-reorder-hint">
          <GripVertical aria-hidden="true" size={14} />
          {t("builder.schedule.reorderHelp")}
        </p>
      </header>
      <div className="lecture-schedule-list" role="list">
        {schedule.map((lecture, index) => (
          <div
            className={`lecture-schedule-row${dropIndex === index ? " is-drop-target" : ""}`}
            key={`${lecture.material_path ?? lecture.title}-${lecture.date}`}
            onDragOver={(event) => {
              event.preventDefault();
              if (!disabled && draggedIndex !== null) setDropIndex(index);
            }}
            onDrop={(event) => {
              event.preventDefault();
              if (!disabled && draggedIndex !== null) moveLecture(draggedIndex, index);
              setDraggedIndex(null);
              setDropIndex(null);
            }}
            role="listitem"
          >
            <div className="lecture-schedule-fields">
              <div className="lecture-schedule-number-field">
                <span>{t("builder.schedule.number")}</span>
                <div className="lecture-schedule-number-controls">
                  <button
                    aria-label={t("builder.schedule.drag", { number: lecture.number })}
                    className="lecture-schedule-drag-handle"
                    disabled={disabled}
                    draggable={!disabled}
                    onDragEnd={() => {
                      setDraggedIndex(null);
                      setDropIndex(null);
                    }}
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = "move";
                      event.dataTransfer.setData("text/plain", String(index));
                      setDraggedIndex(index);
                    }}
                    type="button"
                  >
                    <GripVertical aria-hidden="true" size={17} />
                  </button>
                  <input
                    aria-label={t("builder.schedule.number")}
                    value={lecture.number}
                    onChange={(event) =>
                      onChange(updateSchedule(schedule, index, "number", event.target.value))
                    }
                  />
                  <div className="lecture-schedule-move-buttons">
                    <button
                      aria-label={t("builder.schedule.moveUp", { number: lecture.number })}
                      disabled={disabled || index === 0}
                      onClick={() => moveLecture(index, index - 1)}
                      type="button"
                    >
                      <ArrowUp aria-hidden="true" size={12} />
                    </button>
                    <button
                      aria-label={t("builder.schedule.moveDown", { number: lecture.number })}
                      disabled={disabled || index === schedule.length - 1}
                      onClick={() => moveLecture(index, index + 1)}
                      type="button"
                    >
                      <ArrowDown aria-hidden="true" size={12} />
                    </button>
                  </div>
                </div>
              </div>
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
                  type="date"
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
