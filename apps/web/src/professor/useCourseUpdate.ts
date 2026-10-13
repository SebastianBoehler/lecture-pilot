import { useState } from "react";

import { runBoundedTasks } from "../shared/boundedTaskPool";
import { errorMessage } from "../shared/errorMessage";
import type { LoginSession } from "../shared/types";
import {
  applyCourseUpdate,
  createCourseUpdate,
  discardCourseUpdate,
  getCourseUpdate,
  uploadCourseUpdateMaterial,
} from "./courseUpdateApi";
import {
  buildSelections,
  defaultManualLectures,
  type FileAssignment,
  type ManualLecture,
} from "./courseUpdateSelections";
import type { CourseUpdateAnalysis, CourseUpdateLectureCandidate } from "./courseUpdateTypes";
import { isSkippableUploadError, uploadDestination } from "./professorUpload";

type Field = keyof ManualLecture;

/** Stages changed materials, compares them with the course, and applies the reviewed update. */
export function useCourseUpdate(courseId: string, session: LoginSession, onApplied: () => void) {
  const [files, setFiles] = useState<File[]>([]);
  const [analysis, setAnalysis] = useState<CourseUpdateAnalysis | null>(null);
  const [candidates, setCandidates] = useState<CourseUpdateLectureCandidate[]>([]);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [assignments, setAssignments] = useState<Record<string, FileAssignment>>({});
  const [manual, setManual] = useState<Record<string, ManualLecture>>({});
  const [updateId, setUpdateId] = useState<string | null>(null);
  const [ignored, setIgnored] = useState<string[]>([]);
  const [busy, setBusy] = useState<"upload" | "analyze" | "apply" | null>(null);
  const [uploadProgress, setUploadProgress] = useState({ completed: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);

  const selections = analysis
    ? buildSelections(analysis, candidates, selected, assignments, manual)
    : [];

  async function compare() {
    if (!files.length || busy) return;
    setBusy("upload");
    setUploadProgress({ completed: 0, total: files.length });
    setError(null);
    try {
      if (updateId) await discardCourseUpdate(courseId, updateId, session);
      const created = await createCourseUpdate(courseId, session);
      setUpdateId(created.update_id);
      const skipped: string[] = [];
      await runBoundedTasks(files, 6, async (file) => {
        const path = uploadDestination(file);
        try {
          await uploadCourseUpdateMaterial({
            courseId,
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
      const next = await getCourseUpdate(courseId, created.update_id, session);
      setIgnored(skipped);
      setAnalysis(next);
      setCandidates(next.candidates);
      setSelected(new Set(next.candidates.map((item) => item.candidate_id)));
      setAssignments(Object.fromEntries(next.unassigned_files.map(({ path }) => [path, "ignore"])));
      setManual(defaultManualLectures(next));
    } catch (cause) {
      setError(errorMessage(cause, "Course update comparison failed."));
    } finally {
      setBusy(null);
    }
  }

  async function apply() {
    if (!analysis || !updateId || busy || !selections.length) return;
    setBusy("apply");
    setError(null);
    try {
      await applyCourseUpdate(courseId, updateId, selections, session);
      setUpdateId(null);
      onApplied();
    } catch (cause) {
      setError(errorMessage(cause, "Course update could not be applied."));
    } finally {
      setBusy(null);
    }
  }

  return {
    analysis,
    assignments,
    busy,
    candidates,
    error,
    files,
    canApply: selections.length > 0,
    ignored,
    manual,
    selected,
    uploadProgress,
    compare,
    apply,
    chooseFiles(next: File[]) {
      setFiles(next);
      setAnalysis(null);
      setError(null);
    },
    setAssignment(path: string, value: FileAssignment) {
      setAssignments((current) => ({ ...current, [path]: value }));
    },
    setManual(path: string, field: Field, value: string) {
      setManual((current) => ({ ...current, [path]: { ...current[path], [field]: value } }));
    },
    toggleCandidate(id: string) {
      setSelected((current) => {
        const next = new Set(current);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    updateCandidate(id: string, field: Field, value: string) {
      setCandidates((current) =>
        current.map((item) => (item.candidate_id === id ? { ...item, [field]: value } : item)),
      );
    },
    /** Drops an unapplied staged update; the live course never changes without apply. */
    async discard() {
      if (updateId) await discardCourseUpdate(courseId, updateId, session).catch(() => undefined);
    },
  };
}
