import { useEffect, useEffectEvent } from "react";

import { getPracticeDesign } from "./practiceDesignApi";
import type { PracticeDesign } from "./practiceDesignTypes";
import { useProfessorPracticeDesigns } from "./useProfessorPracticeDesigns";
import type { LoginSession } from "./types";

export type PracticeDesignLecture = { id: string; label: string };

export function useProfessorPracticeDesignGate({
  courseId,
  routingReady,
  session,
  sourceRevision,
  targetLectures,
}: {
  courseId: string | null;
  routingReady: boolean;
  session: LoginSession;
  sourceRevision: string | null;
  targetLectures: PracticeDesignLecture[];
}) {
  const designs = useProfessorPracticeDesigns({ courseId, session });
  const lectureIds = targetLectures.map((lecture) => lecture.id);
  const lectureKey = lectureIds.join("|");
  const load = useEffectEvent(() => designs.loadAll(lectureIds));
  const designReady = Boolean(
    sourceRevision &&
    lectureIds.length &&
    lectureIds.every((lectureId) =>
      isCurrentPracticeApproval(designs.designs[lectureId], sourceRevision),
    ),
  );

  useEffect(() => {
    if (!courseId || !sourceRevision || !lectureKey) return;
    void load();
  }, [courseId, lectureKey, sourceRevision]);

  return {
    designReady,
    practiceDesignStep: {
      designs: designs.designs,
      error: designs.error,
      lectures: targetLectures,
      pendingAction: designs.pendingAction,
      pendingLectureId: designs.pendingLectureId,
      routingReady,
      onApprove: (lectureId: string) => void designs.approve(lectureId),
      onPropose: (lectureId: string, refresh = false) => void designs.propose(lectureId, refresh),
      onReview: (lectureId: string) => void designs.review(lectureId),
      onSave: (lectureId: string, update: Parameters<typeof designs.save>[1]) =>
        void designs.save(lectureId, update),
    },
    requireCurrentApprovals: (expectedSourceRevision: string) =>
      requireCurrentPracticeApprovals({
        courseId,
        lectureIds,
        session,
        sourceRevision: expectedSourceRevision,
      }),
    reset: () => designs.reset(lectureIds),
  };
}

export async function requireCurrentPracticeApprovals({
  courseId,
  lectureIds,
  session,
  sourceRevision,
}: {
  courseId: string | null;
  lectureIds: readonly string[];
  session: LoginSession;
  sourceRevision: string;
}) {
  if (!courseId || !lectureIds.length) throw missingApproval();
  const designs = await Promise.all(
    lectureIds.map((lectureId) => getPracticeDesign({ courseId, lectureId, session })),
  );
  if (!designs.every((design) => isCurrentPracticeApproval(design, sourceRevision))) {
    throw missingApproval();
  }
}

export function isCurrentPracticeApproval(
  design: PracticeDesign | undefined,
  sourceRevision: string,
) {
  return Boolean(
    design?.approval &&
    design.source_revision === sourceRevision &&
    design.approval.source_revision === sourceRevision &&
    design.approval.practice_design_revision === design.revision,
  );
}

function missingApproval() {
  return new Error("Generate and approve the lecture learning plan before generating its canvas.");
}
