import { useEffect, useState } from "react";

import { sameEditableDesign } from "./ProfessorPracticeDesignStep.helpers";
import type { PracticeDesign } from "./practiceDesignTypes";

type DraftEntry = Readonly<{
  base: PracticeDesign;
  conflict: boolean;
  draft: PracticeDesign;
}>;

export function usePracticeDesignDrafts({
  designs,
  lectureIds,
}: {
  designs: Readonly<Record<string, PracticeDesign>>;
  lectureIds: readonly string[];
}) {
  const [entries, setEntries] = useState<Readonly<Record<string, DraftEntry>>>({});
  useEffect(() => {
    setEntries((current) => reconcileEntries(current, designs, lectureIds));
  }, [designs, lectureIds]);

  return {
    conflicts: Object.fromEntries(
      Object.entries(entries).map(([lectureId, entry]) => [lectureId, entry.conflict]),
    ) as Readonly<Record<string, boolean>>,
    drafts: Object.fromEntries(
      Object.entries(entries).map(([lectureId, entry]) => [lectureId, entry.draft]),
    ) as Readonly<Record<string, PracticeDesign>>,
    change(lectureId: string, draft: PracticeDesign) {
      setEntries((current) => {
        const entry = current[lectureId];
        return entry ? { ...current, [lectureId]: { ...entry, draft } } : current;
      });
    },
    useLatest(lectureId: string) {
      const design = designs[lectureId];
      if (!design) return;
      setEntries((current) => ({
        ...current,
        [lectureId]: { base: design, conflict: false, draft: design },
      }));
    },
  };
}

function reconcileEntries(
  current: Readonly<Record<string, DraftEntry>>,
  designs: Readonly<Record<string, PracticeDesign>>,
  lectureIds: readonly string[],
) {
  return Object.fromEntries(
    lectureIds.flatMap((lectureId) => {
      const design = designs[lectureId];
      if (!design) return [];
      const entry = current[lectureId];
      if (!entry) return [[lectureId, { base: design, conflict: false, draft: design }]];
      if (entry.base.revision === design.revision) return [[lectureId, entry]];
      if (!isDirty(entry) || sameEditableContent(entry.draft, design)) {
        return [[lectureId, { base: design, conflict: false, draft: design }]];
      }
      return [[lectureId, { ...entry, conflict: true }]];
    }),
  );
}

function isDirty(entry: DraftEntry) {
  return !sameEditableDesign(entry.draft, entry.base);
}

function sameEditableContent(left: PracticeDesign, right: PracticeDesign) {
  return JSON.stringify(editableContent(left)) === JSON.stringify(editableContent(right));
}

function editableContent(design: PracticeDesign) {
  return {
    lecture_title: design.lecture_title,
    objective: design.objective,
    planning_context: design.planning_context,
    source_revision: design.source_revision,
    targets: design.targets,
  };
}
