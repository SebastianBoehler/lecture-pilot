import { useEffect, useState, type ReactNode } from "react";
import { apiUrl, readApiError } from "./api";
import { learnerRequestInit } from "./authz";
import { PredictionContext, type CanvasPrediction } from "./predictionContext";
import type { LearnerWorkspaceMode, LoginSession } from "./types";

export function LessonPredictions({
  courseId,
  lectureId,
  session,
  mode,
  publicationVersion,
  enabled,
  children,
}: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
  mode: LearnerWorkspaceMode;
  publicationVersion: number | null;
  enabled: boolean;
  children: ReactNode;
}) {
  const [saved, setSaved] = useState<CanvasPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const path = `/courses/${encodeURIComponent(courseId)}/lectures/${encodeURIComponent(lectureId)}/predictions`;
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setLoading(true);
    setSaved([]);
    setError(null);
    void fetch(apiUrl(path), learnerRequestInit(session, mode, { signal: controller.signal }))
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok)
          throw new Error(readApiError(payload, "Predictions could not be loaded."));
        if (!Array.isArray(payload)) throw new Error("Invalid prediction response.");
        if (!controller.signal.aborted) setSaved(payload);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : "Predictions could not be loaded.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, session, mode, publicationVersion, enabled]);

  async function save(blockId: string, answer: string | null) {
    if (!enabled || !publicationVersion || loading || error)
      throw new Error("Reload this lecture before saving a prediction.");
    const response = await fetch(
      apiUrl(path),
      learnerRequestInit(session, mode, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          block_id: blockId,
          answer,
          publication_version: publicationVersion,
        }),
      }),
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(readApiError(payload, "Prediction could not be saved."));
    setSaved((current) => [...current.filter((item) => item.block_id !== blockId), payload]);
  }
  return (
    <PredictionContext.Provider value={enabled ? { saved, loading, error, save } : null}>
      {children}
    </PredictionContext.Provider>
  );
}
