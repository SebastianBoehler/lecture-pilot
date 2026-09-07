import { useEffect, useState, type ReactNode } from "react";

import { apiUrl, readApiError } from "./api";
import { learnerRequestInit } from "./authz";
import { CanvasAnnotationContext, type CanvasAnnotation } from "./canvasAnnotationContext";
import type { LearnerWorkspaceMode, LoginSession } from "./types";

export function LessonAnnotations({
  courseId,
  lectureId,
  session,
  mode,
  revision,
  enabled = true,
  children,
}: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
  mode: LearnerWorkspaceMode;
  revision: number;
  enabled?: boolean;
  children: ReactNode;
}) {
  const [annotations, setAnnotations] = useState<CanvasAnnotation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const path = `/courses/${courseId}/lectures/${lectureId}/annotations`;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    async function load() {
      try {
        const response = await fetch(apiUrl(path), learnerRequestInit(session, mode));
        const payload = await response.json();
        if (!response.ok)
          throw new Error(readApiError(payload, "Annotations could not be loaded."));
        if (!Array.isArray(payload)) throw new Error("Annotation response is invalid.");
        if (!cancelled) {
          setAnnotations(payload);
          setError(null);
        }
      } catch (reason) {
        if (!cancelled) {
          setAnnotations([]);
          setError(reason instanceof Error ? reason.message : "Annotations could not be loaded.");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [path, session, mode, revision, enabled]);

  async function remove(id: string) {
    if (!enabled) throw new Error("Draft annotations are unavailable.");
    const response = await fetch(
      apiUrl(`${path}/${id}`),
      learnerRequestInit(session, mode, { method: "DELETE" }),
    );
    if (!response.ok)
      throw new Error(readApiError(await response.json(), "Annotation could not be deleted."));
    setAnnotations((current) => current.filter((note) => note.id !== id));
  }

  return (
    <CanvasAnnotationContext.Provider value={{ annotations: enabled ? annotations : [], remove }}>
      {enabled && error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {children}
    </CanvasAnnotationContext.Provider>
  );
}
