import type { LearningIntentApprovalOptions } from "./learningIntentTypes";
import { useEffect, useEffectEvent, useState } from "react";

import { getPracticeDesignReadiness } from "./practiceDesignApi";
import { isPracticeDesignReady } from "./practiceDesignReadiness";
import { useProfessorPracticeDesigns } from "./useProfessorPracticeDesigns";
import type { LoginSession } from "./types";

export type PracticeDesignLecture = { id: string; label: string };

export function useProfessorPracticeDesignGate({
  courseId,
  routingReady,
  session,
  targetLectures,
}: {
  courseId: string | null;
  routingReady: boolean;
  session: LoginSession;
  targetLectures: PracticeDesignLecture[];
}) {
  const designs = useProfessorPracticeDesigns({ courseId, session });
  const lectureIds = targetLectures.map((lecture) => lecture.id);
  const lectureKey = lectureIds.join("|");
  const [preparing, setPreparing] = useState(false);
  const load = useEffectEvent(() => designs.loadAll(lectureIds, routingReady));
  const designReady = Boolean(
    lectureIds.length &&
    lectureIds.every((lectureId) =>
      isPracticeDesignReady(designs.designs[lectureId], designs.readiness[lectureId]),
    ),
  );

  useEffect(() => {
    if (!courseId || !lectureKey) return;
    let cancelled = false;
    setPreparing(routingReady);
    void load().finally(() => {
      if (!cancelled) setPreparing(false);
    });
    return () => {
      cancelled = true;
    };
  }, [courseId, lectureKey, routingReady]);

  return {
    designReady,
    practiceDesignStep: {
      designs: designs.designs,
      preparing,
      pendingByLecture: designs.pendingByLecture,
      error: designs.error,
      errorsByLecture: designs.errorsByLecture,
      lectures: targetLectures,
      pendingAction: designs.pendingAction,
      pendingLectureId: designs.pendingLectureId,
      routingReady,
      onApprove: (lectureId: string, intent?: LearningIntentApprovalOptions) =>
        void designs.approve(lectureId, intent),
      onPropose: (lectureId: string, refresh = false) => void designs.propose(lectureId, refresh),
      onReview: (lectureId: string) => void designs.review(lectureId),
      onReload: (lectureId: string) => designs.load(lectureId),
      onSave: (lectureId: string, update: Parameters<typeof designs.save>[1]) =>
        void designs.save(lectureId, update),
    },
    requireCurrentApprovals: () =>
      requireCurrentPracticeApprovals({
        courseId,
        lectureIds,
        session,
      }),
    reset: () => designs.reset(lectureIds),
  };
}

export async function requireCurrentPracticeApprovals({
  courseId,
  lectureIds,
  session,
}: {
  courseId: string | null;
  lectureIds: readonly string[];
  session: LoginSession;
}) {
  if (!courseId || !lectureIds.length) throw missingApproval();
  const readiness = await Promise.all(
    lectureIds.map((lectureId) => getPracticeDesignReadiness({ courseId, lectureId, session })),
  );
  if (!readiness.every((status) => status.ready_for_generation)) {
    throw missingApproval();
  }
}

function missingApproval() {
  return new Error("Generate and approve the lecture learning plan before generating its canvas.");
}
