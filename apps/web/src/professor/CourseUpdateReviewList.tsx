import { useI18n } from "../i18n/i18n";
import type { ManualLecture } from "./courseUpdateSelections";
import type { CourseUpdateAnalysis, CourseUpdateLectureCandidate } from "./courseUpdateTypes";

type Field = keyof ManualLecture;

/** Compact review of a comparison: unchanged count, changed and new lectures, open file decisions. */
export function CourseUpdateReviewList({
  analysis,
  assignments,
  candidates,
  disabled,
  manual,
  selected,
  onAssignment,
  onCandidateChange,
  onManualChange,
  onToggle,
}: {
  analysis: CourseUpdateAnalysis;
  assignments: Readonly<Record<string, string>>;
  candidates: readonly CourseUpdateLectureCandidate[];
  disabled: boolean;
  manual: Readonly<Record<string, ManualLecture>>;
  selected: ReadonlySet<string>;
  onAssignment: (path: string, value: string) => void;
  onCandidateChange: (id: string, field: Field, value: string) => void;
  onManualChange: (path: string, field: Field, value: string) => void;
  onToggle: (id: string) => void;
}) {
  const { t } = useI18n();
  const changed = candidates.filter((item) => item.action === "update");
  const added = candidates.filter((item) => item.action === "new");
  const fileCount = (count: number) =>
    count === 1 ? t("courseUpdate.fileOne") : t("courseUpdate.files", { count });

  if (!candidates.length && !analysis.unassigned_files.length) {
    return <p className="update-empty">{t("courseUpdate.noChanges")}</p>;
  }
  return (
    <div className="update-review">
      {analysis.unchanged_files ? (
        <details className="update-group">
          <summary>
            {t("courseUpdate.unchanged")} <span>{analysis.unchanged_files}</span>
          </summary>
          <p>{t("courseUpdate.unchangedCount", { count: analysis.unchanged_files })}</p>
        </details>
      ) : null}
      {changed.length ? (
        <section className="update-group" aria-labelledby="update-changed">
          <h3 id="update-changed">{t("courseUpdate.changedLectures")}</h3>
          <ul>
            {changed.map((item) => (
              <li key={item.candidate_id} className="update-item">
                {include(item)}
                <span className="update-item-meta">{fileCount(item.file_paths.length)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {added.length ? (
        <section className="update-group" aria-labelledby="update-new">
          <h3 id="update-new">{t("courseUpdate.newLectures")}</h3>
          <ul>
            {added.map((item) => (
              <li key={item.candidate_id} className="update-item">
                {include(item)}
                <span className="update-item-meta">{fileCount(item.file_paths.length)}</span>
                {selected.has(item.candidate_id)
                  ? fields(item, (field, value) =>
                      onCandidateChange(item.candidate_id, field, value),
                    )
                  : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {analysis.unassigned_files.length ? (
        <section className="update-group" aria-labelledby="update-decisions">
          <h3 id="update-decisions">{t("courseUpdate.decisions")}</h3>
          <p>{t("courseUpdate.decisionsHelp")}</p>
          <ul>
            {analysis.unassigned_files.map((file) => {
              const assignment = assignments[file.path] ?? "ignore";
              return (
                <li key={file.path} className="update-item">
                  <div className="update-file">
                    <code>{file.path}</code>
                    <select
                      aria-label={t("courseUpdate.assignFile", { file: file.path })}
                      disabled={disabled}
                      value={assignment}
                      onChange={(event) => onAssignment(file.path, event.target.value)}
                    >
                      <option value="ignore">{t("courseUpdate.ignore")}</option>
                      {analysis.existing_lectures.map((lecture) => (
                        <option key={lecture.lecture_id} value={`lecture:${lecture.lecture_id}`}>
                          {t("courseUpdate.lectureOption", lecture)}
                        </option>
                      ))}
                      <option value="all">{t("courseUpdate.allLectures")}</option>
                      <option value="new">{t("courseUpdate.newLecture")}</option>
                    </select>
                  </div>
                  {assignment === "new" && manual[file.path]
                    ? fields(manual[file.path], (field, value) =>
                        onManualChange(file.path, field, value),
                      )
                    : null}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </div>
  );

  function include(item: CourseUpdateLectureCandidate) {
    return (
      <label className="update-include">
        <input
          checked={selected.has(item.candidate_id)}
          disabled={disabled}
          type="checkbox"
          aria-label={t("courseUpdate.include", { lecture: item.title })}
          onChange={() => onToggle(item.candidate_id)}
        />
        <span>
          <span className="update-item-number">{item.number}</span> {item.title}
        </span>
      </label>
    );
  }

  function fields(value: ManualLecture, onChange: (field: Field, value: string) => void) {
    return (
      <div className="update-fields">
        <label>
          {t("courseUpdate.number")}
          <input
            disabled={disabled}
            inputMode="numeric"
            value={value.number}
            onChange={(event) => onChange("number", event.target.value)}
          />
        </label>
        <label>
          {t("courseUpdate.title")}
          <input
            disabled={disabled}
            value={value.title}
            onChange={(event) => onChange("title", event.target.value)}
          />
        </label>
        <label>
          {t("courseUpdate.date")}
          <input
            disabled={disabled}
            type="date"
            value={value.date}
            onChange={(event) => onChange("date", event.target.value)}
          />
        </label>
      </div>
    );
  }
}
