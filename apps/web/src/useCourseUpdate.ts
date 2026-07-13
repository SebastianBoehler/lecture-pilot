import { useMemo, useState } from "react";

import { draftLectureCanvas, publishLectureCanvas } from "./api";
import {
  applyCourseUpdate,
  createCourseUpdate,
  discardCourseUpdate,
  getCourseUpdate,
  uploadCourseUpdateMaterial,
} from "./courseUpdateApi";
import type {
  CourseUpdateAnalysis,
  CourseUpdateApplyResult,
  CourseUpdateLectureCandidate,
  CourseUpdateLectureSelection,
} from "./courseUpdateTypes";
import { isSkippableUploadError, uploadDestination } from "./professorUpload";
import type { CourseWorkspaceResult, LoginSession } from "./types";

type WorkStatus = "waiting" | "drafting" | "ready" | "failed" | "publishing" | "published";
type ManualLecture = { number: string; title: string; date: string };

export function useCourseUpdate(
  workspace: CourseWorkspaceResult,
  session: LoginSession,
  onApplied: (workspace: CourseWorkspaceResult) => void,
) {
  const [files, setFiles] = useState<File[]>([]);
  const [analysis, setAnalysis] = useState<CourseUpdateAnalysis | null>(null);
  const [candidates, setCandidates] = useState<CourseUpdateLectureCandidate[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [manual, setManual] = useState<Record<string, ManualLecture>>({});
  const [updateId, setUpdateId] = useState<string | null>(null);
  const [result, setResult] = useState<CourseUpdateApplyResult | null>(null);
  const [statuses, setStatuses] = useState<Record<string, WorkStatus>>({});
  const [ignored, setIgnored] = useState<string[]>([]);
  const [busy, setBusy] = useState<
    "upload" | "analyze" | "apply" | "draft" | "publish" | null
  >(null);
  const [uploadProgress, setUploadProgress] = useState({ completed: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);

  const hasSelection = useMemo(
    () => selected.size > 0 || Object.values(assignments).some((value) => value !== "ignore"),
    [assignments, selected],
  );

  return {
    analysis,
    assignments,
    busy,
    candidates,
    error,
    files,
    hasSelection,
    ignored,
    manual,
    result,
    selected,
    statuses,
    uploadProgress,
    setAssignment(path: string, value: string) {
      setAssignments((current) => ({ ...current, [path]: value }));
    },
    setFiles(next: File[]) {
      setFiles(next);
      setAnalysis(null);
      setResult(null);
      setError(null);
    },
    setManual(path: string, field: "number" | "title" | "date", value: string) {
      setManual((current) => ({
        ...current,
        [path]: { ...current[path], [field]: value },
      }));
    },
    toggleCandidate(id: string) {
      setSelected((current) => {
        const next = new Set(current);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    updateCandidate(id: string, field: "number" | "title" | "date", value: string) {
      setCandidates((current) =>
        current.map((item) => (item.candidate_id === id ? { ...item, [field]: value } : item)),
      );
    },
    compare: async () => {
      if (!files.length || busy) return;
      setBusy("upload");
      setUploadProgress({ completed: 0, total: files.length });
      setError(null);
      try {
        if (updateId) await discardCourseUpdate(workspace.course.id, updateId, session);
        const created = await createCourseUpdate(workspace.course.id, session);
        setUpdateId(created.update_id);
        const skipped: string[] = [];
        await uploadPool(files, 6, async (file) => {
          const path = uploadDestination("uploads", file, files.length);
          try {
            await uploadCourseUpdateMaterial({
              courseId: workspace.course.id,
              updateId: created.update_id,
              path,
              file,
              session,
            });
          } catch (uploadError) {
            if (!isSkippableUploadError(uploadError)) throw uploadError;
            skipped.push(path);
          } finally {
            setUploadProgress((current) => ({ ...current, completed: current.completed + 1 }));
          }
        });
        setBusy("analyze");
        const next = await getCourseUpdate(workspace.course.id, created.update_id, session);
        setIgnored(skipped);
        setAnalysis(next);
        setCandidates(next.candidates);
        setSelected(new Set(next.candidates.map((item) => item.candidate_id)));
        setAssignments(
          Object.fromEntries(next.unassigned_files.map((item) => [item.path, "ignore"])),
        );
        setManual(defaultManual(next));
      } catch (cause) {
        setError(message(cause));
      } finally {
        setBusy(null);
      }
    },
    apply: async () => {
      if (!analysis || !updateId || busy) return;
      const lectures = buildSelections(analysis, candidates, selected, assignments, manual);
      if (!lectures.length) {
        setError("Select at least one lecture or assign one file before continuing.");
        return;
      }
      setBusy("apply");
      setError(null);
      try {
        const applied = await applyCourseUpdate(workspace.course.id, updateId, lectures, session);
        setResult(applied);
        onApplied(applied.workspace);
        setStatuses(Object.fromEntries(applied.affected_lecture_ids.map((id) => [id, "waiting"])));
        await generateDrafts(applied.affected_lecture_ids);
      } catch (cause) {
        setError(message(cause));
      } finally {
        setBusy(null);
      }
    },
    retryDrafts: async () => {
      if (!result || busy) return;
      const targets = result.affected_lecture_ids.filter((id) => statuses[id] !== "ready");
      await generateDrafts(targets);
    },
    publish: async () => {
      if (!result || busy) return;
      const targets = result.affected_lecture_ids.filter((id) => statuses[id] === "ready");
      setBusy("publish");
      setError(null);
      let activeId: string | null = null;
      try {
        for (const id of targets) {
          activeId = id;
          setStatuses((current) => ({ ...current, [id]: "publishing" }));
          await publishLectureCanvas(workspace.course.id, id, session);
          setStatuses((current) => ({ ...current, [id]: "published" }));
          activeId = null;
        }
      } catch (cause) {
        if (activeId) {
          const failedId = activeId;
          setStatuses((current) => ({ ...current, [failedId]: "ready" }));
        }
        setError(message(cause));
      } finally {
        setBusy(null);
      }
    },
    cancel: async () => {
      if (updateId && !result) {
        await discardCourseUpdate(workspace.course.id, updateId, session).catch(() => undefined);
      }
    },
  };

  async function generateDrafts(ids: string[]) {
    setBusy("draft");
    let failed = false;
    for (const id of ids) {
      setStatuses((current) => ({ ...current, [id]: "drafting" }));
      try {
        await draftLectureCanvas(workspace.course.id, id, session);
        setStatuses((current) => ({ ...current, [id]: "ready" }));
      } catch {
        failed = true;
        setStatuses((current) => ({ ...current, [id]: "failed" }));
      }
    }
    if (failed)
      setError("Some drafts could not be generated. The published versions are unchanged.");
    setBusy(null);
  }
}

function buildSelections(
  analysis: CourseUpdateAnalysis,
  candidates: CourseUpdateLectureCandidate[],
  selected: Set<string>,
  assignments: Record<string, string>,
  manual: Record<string, ManualLecture>,
) {
  const selections = new Map<string, CourseUpdateLectureSelection>();
  const merge = (key: string, item: CourseUpdateLectureSelection, paths: string[]) => {
    const current = selections.get(key);
    selections.set(
      key,
      current ? { ...current, file_paths: [...new Set([...current.file_paths, ...paths])] } : item,
    );
  };
  for (const item of candidates.filter((candidate) => selected.has(candidate.candidate_id))) {
    const key = item.lecture_id ?? item.candidate_id;
    merge(
      key,
      {
        lecture_id: item.lecture_id,
        number: item.number,
        title: item.title,
        date: item.date,
        file_paths: item.file_paths,
      },
      item.file_paths,
    );
  }
  for (const file of analysis.unassigned_files) {
    const assignment = assignments[file.path] ?? "ignore";
    const targets =
      assignment === "all"
        ? analysis.existing_lectures.map((item) => item.lecture_id)
        : assignment.startsWith("lecture:")
          ? [assignment.slice(8)]
          : [];
    for (const id of targets) {
      const lecture = analysis.existing_lectures.find((item) => item.lecture_id === id);
      if (lecture) merge(id, { ...lecture, file_paths: [file.path] }, [file.path]);
    }
    if (assignment === "new" && manual[file.path]) {
      merge(`manual:${file.path}`, { ...manual[file.path], file_paths: [file.path] }, [file.path]);
    }
  }
  return [...selections.values()];
}

function defaultManual(analysis: CourseUpdateAnalysis) {
  const last = analysis.existing_lectures.at(-1);
  const next =
    Math.max(0, ...analysis.existing_lectures.map((item) => Number(item.number) || 0)) + 1;
  const date = new Date(`${last?.date ?? new Date().toISOString().slice(0, 10)}T12:00:00`);
  date.setDate(date.getDate() + 7);
  return Object.fromEntries(
    analysis.unassigned_files.map((item, index) => [
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

async function uploadPool<T>(items: T[], concurrency: number, task: (item: T) => Promise<void>) {
  let index = 0;
  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, async () => {
      while (index < items.length) await task(items[index++]);
    }),
  );
}

function message(cause: unknown) {
  return cause instanceof Error ? cause.message : "Course update failed.";
}
