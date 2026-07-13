import { useI18n } from "./i18n";
import type { CourseUpdateAnalysis, CourseUpdateLectureCandidate } from "./courseUpdateTypes";

export function CourseUpdateReview({
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
  assignments: Record<string, string>;
  candidates: CourseUpdateLectureCandidate[];
  disabled: boolean;
  manual: Record<string, { number: string; title: string; date: string }>;
  selected: Set<string>;
  onAssignment: (path: string, value: string) => void;
  onCandidateChange: (id: string, field: "number" | "title" | "date", value: string) => void;
  onManualChange: (path: string, field: "number" | "title" | "date", value: string) => void;
  onToggle: (id: string) => void;
}) {
  const { t } = useI18n();
  return (
    <section className="course-update-review" aria-labelledby="course-update-review-title">
      <div>
        <h2 id="course-update-review-title">{t("courseUpdate.reviewTitle")}</h2>
        <p>{t("courseUpdate.reviewHelp")}</p>
      </div>
      {analysis.unchanged_files ? (
        <p className="course-update-summary">
          {t("courseUpdate.unchanged", { count: analysis.unchanged_files })}
        </p>
      ) : null}
      {candidates.map((candidate) => (
        <article className="course-update-candidate" key={candidate.candidate_id}>
          <label className="course-update-toggle">
            <input
              checked={selected.has(candidate.candidate_id)}
              disabled={disabled}
              type="checkbox"
              onChange={() => onToggle(candidate.candidate_id)}
            />
            <span>
              <strong>{candidate.title}</strong>
              <small className="course-update-candidate-meta">
                <span className="course-update-badge">
                  {candidate.action === "new"
                    ? t("courseUpdate.newLecture")
                    : t("courseUpdate.existingLecture")}
                </span>
                <span>{t("courseUpdate.files", { count: candidate.file_paths.length })}</span>
              </small>
            </span>
          </label>
          {selected.has(candidate.candidate_id) ? (
            <div className="course-update-fields">
              <label>
                {t("courseUpdate.number")}
                <input
                  disabled={disabled || candidate.action === "update"}
                  value={candidate.number}
                  onChange={(event) =>
                    onCandidateChange(candidate.candidate_id, "number", event.target.value)
                  }
                />
              </label>
              <label>
                {t("courseUpdate.title")}
                <input
                  disabled={disabled}
                  value={candidate.title}
                  onChange={(event) =>
                    onCandidateChange(candidate.candidate_id, "title", event.target.value)
                  }
                />
              </label>
              <label>
                {t("courseUpdate.date")}
                <input
                  disabled={disabled}
                  type="date"
                  value={candidate.date}
                  onChange={(event) =>
                    onCandidateChange(candidate.candidate_id, "date", event.target.value)
                  }
                />
              </label>
            </div>
          ) : null}
          <details>
            <summary>{t("courseUpdate.showFiles")}</summary>
            <ul>
              {candidate.file_paths.map((path) => (
                <li key={path}>{path}</li>
              ))}
            </ul>
          </details>
        </article>
      ))}
      {analysis.unassigned_files.length ? (
        <div className="course-update-unassigned">
          <h3>{t("courseUpdate.unassignedTitle")}</h3>
          <p>{t("courseUpdate.unassignedHelp")}</p>
          {analysis.unassigned_files.map((file) => {
            const assignment = assignments[file.path] ?? "ignore";
            const fields = manual[file.path];
            return (
              <div className="course-update-unassigned-row" key={file.path}>
                <code>{file.path}</code>
                <label>
                  <span className="sr-only">
                    {t("courseUpdate.assignFile", { file: file.path })}
                  </span>
                  <select
                    disabled={disabled}
                    value={assignment}
                    onChange={(event) => onAssignment(file.path, event.target.value)}
                  >
                    <option value="ignore">{t("courseUpdate.ignore")}</option>
                    <option value="all">{t("courseUpdate.allLectures")}</option>
                    {analysis.existing_lectures.map((lecture) => (
                      <option key={lecture.lecture_id} value={`lecture:${lecture.lecture_id}`}>
                        {lecture.number} · {lecture.title}
                      </option>
                    ))}
                    <option value="new">{t("courseUpdate.createLecture")}</option>
                  </select>
                </label>
                {assignment === "new" && fields ? (
                  <div className="course-update-fields">
                    <label>
                      {t("courseUpdate.number")}
                      <input
                        disabled={disabled}
                        value={fields.number}
                        onChange={(event) =>
                          onManualChange(file.path, "number", event.target.value)
                        }
                      />
                    </label>
                    <label>
                      {t("courseUpdate.title")}
                      <input
                        disabled={disabled}
                        value={fields.title}
                        onChange={(event) => onManualChange(file.path, "title", event.target.value)}
                      />
                    </label>
                    <label>
                      {t("courseUpdate.date")}
                      <input
                        disabled={disabled}
                        type="date"
                        value={fields.date}
                        onChange={(event) => onManualChange(file.path, "date", event.target.value)}
                      />
                    </label>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
      {!candidates.length && !analysis.unassigned_files.length ? (
        <p className="course-update-empty">{t("courseUpdate.noChanges")}</p>
      ) : null}
    </section>
  );
}
