import { useEffect, useEffectEvent } from "react";

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
  const load = useEffectEvent(() => designs.loadAll(lectureIds));
  const designReady = Boolean(
    lectureIds.length &&
    lectureIds.every((lectureId) =>
      isPracticeDesignReady(designs.designs[lectureId], designs.readiness[lectureId]),
    ),
  );

  useEffect(() => {
    if (!courseId || !lectureKey) return;
    void load();
  }, [courseId, lectureKey]);

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
