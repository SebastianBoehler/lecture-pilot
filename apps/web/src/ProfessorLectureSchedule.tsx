import { useState } from "react";
import { GripVertical, Trash2 } from "lucide-react";

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
  const [reorderAnnouncement, setReorderAnnouncement] = useState("");
  const moveLecture = (fromIndex: number, toIndex: number) => {
    if (toIndex < 0 || toIndex >= schedule.length || fromIndex === toIndex) return;
    const lecture = schedule[fromIndex];
    onChange(reorderLectureSchedule(schedule, fromIndex, toIndex));
    setReorderAnnouncement(
      t("builder.schedule.moved", { title: lecture.title, position: toIndex + 1 }),
    );
  };
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
        <p className="visually-hidden" role="status" aria-live="polite">
          {reorderAnnouncement}
        </p>
      </header>
      <div className="lecture-schedule-column-headings" aria-hidden="true">
        <span>{t("builder.schedule.order")}</span>
        <span>{t("builder.schedule.lectureTitle")}</span>
        <span>{t("builder.schedule.date")}</span>
        <span />
      </div>
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
                <span className="lecture-schedule-row-label">{t("builder.schedule.order")}</span>
                <div className="lecture-schedule-number-controls">
                  <div
                    aria-disabled={disabled}
                    aria-keyshortcuts="ArrowUp ArrowDown"
                    aria-label={t("builder.schedule.position", { number: lecture.number })}
                    aria-valuemax={schedule.length}
                    aria-valuemin={1}
                    aria-valuenow={index + 1}
                    aria-valuetext={t("builder.schedule.positionValue", {
                      title: lecture.title,
                      position: index + 1,
                      count: schedule.length,
                    })}
                    className="lecture-schedule-drag-handle"
                    draggable={!disabled}
                    role="spinbutton"
                    tabIndex={disabled ? -1 : 0}
                    title={t("builder.schedule.drag", { number: lecture.number })}
                    onDragEnd={() => {
                      setDraggedIndex(null);
                      setDropIndex(null);
                    }}
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = "move";
                      event.dataTransfer.setData("text/plain", String(index));
                      setDraggedIndex(index);
                    }}
                    onKeyDown={(event) => {
                      if (disabled || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
                      event.preventDefault();
                      moveLecture(index, index + (event.key === "ArrowUp" ? -1 : 1));
                    }}
                  >
                    <GripVertical aria-hidden="true" size={18} />
                  </div>
                  <span className="lecture-schedule-position-number">{lecture.number}</span>
                </div>
              </div>
              <label>
                <span className="lecture-schedule-row-label">
                  {t("builder.schedule.lectureTitle")}
                </span>
                <input
                  value={lecture.title}
                  onChange={(event) =>
                    onChange(updateSchedule(schedule, index, "title", event.target.value))
                  }
                />
              </label>
              <label>
                <span className="lecture-schedule-row-label">{t("builder.schedule.date")}</span>
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
  key: "date" | "title",
  value: string,
) {
  return schedule.map((lecture, currentIndex) =>
    currentIndex === index ? { ...lecture, [key]: value } : lecture,
  );
}
