import type {
  CourseUpdateAnalysis,
  CourseUpdateLectureCandidate,
  CourseUpdateLectureSelection,
} from "./courseUpdateTypes";

export type ManualLecture = { number: string; title: string; date: string };

/** "ignore", "all", "new", or "lecture:<id>" for each file the comparison could not place. */
export type FileAssignment = string;

/** Merges included candidates and file decisions into one apply payload per lecture. */
export function buildSelections(
  analysis: CourseUpdateAnalysis,
  candidates: readonly CourseUpdateLectureCandidate[],
  selected: ReadonlySet<string>,
  assignments: Readonly<Record<string, FileAssignment>>,
  manual: Readonly<Record<string, ManualLecture>>,
) {
  const selections = new Map<string, CourseUpdateLectureSelection>();
  const merge = (key: string, item: CourseUpdateLectureSelection) => {
    const current = selections.get(key);
    selections.set(
      key,
      current
        ? { ...current, file_paths: [...new Set([...current.file_paths, ...item.file_paths])] }
        : item,
    );
  };
  for (const item of candidates.filter((candidate) => selected.has(candidate.candidate_id))) {
    merge(item.lecture_id ?? item.candidate_id, {
      lecture_id: item.lecture_id,
      number: item.number,
      title: item.title,
      date: item.date,
      file_paths: item.file_paths,
    });
  }
  for (const file of analysis.unassigned_files) {
    const assignment = assignments[file.path] ?? "ignore";
    const targets =
      assignment === "all"
        ? analysis.existing_lectures.map((item) => item.lecture_id)
        : assignment.startsWith("lecture:")
          ? [assignment.slice("lecture:".length)]
          : [];
    for (const id of targets) {
      const lecture = analysis.existing_lectures.find((item) => item.lecture_id === id);
      if (lecture) merge(id, { ...lecture, file_paths: [file.path] });
    }
    if (assignment === "new" && manual[file.path]) {
      merge(`manual:${file.path}`, { ...manual[file.path], file_paths: [file.path] });
    }
  }
  return [...selections.values()];
}

/** Suggested number, title and date for a file that becomes a new lecture. */
export function defaultManualLectures(analysis: CourseUpdateAnalysis) {
  const last = analysis.existing_lectures.at(-1);
  const next =
    Math.max(0, ...analysis.existing_lectures.map((item) => Number(item.number) || 0)) + 1;
  const date = new Date(`${last?.date ?? new Date().toISOString().slice(0, 10)}T12:00:00`);
  date.setDate(date.getDate() + 7);
  return Object.fromEntries(
    analysis.unassigned_files.map((item, index): [string, ManualLecture] => [
      item.path,
      {
        number: String(next + index).padStart(2, "0"),
        title:
          item.path
            .split("/")
            .at(-1)
            ?.replace(/\.[^.]+$/, "") || `Lecture ${next + index}`,
        date: date.toISOString().slice(0, 10),
      },
    ]),
  );
}
