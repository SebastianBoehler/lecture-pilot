import { useCallback, useState } from "react";

export type BuilderAction =
  | "apply-schedule"
  | "create"
  | "confirm-routing"
  | "delete-course"
  | "generate"
  | "include-videos"
  | "publish"
  | "regenerate-routing"
  | "search"
  | "suggest-videos"
  | "upload"
  | "validate-routing";

export function useProfessorWorkflowRun() {
  const [pendingAction, setPendingAction] = useState<BuilderAction | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (actionId: BuilderAction, action: () => Promise<string | void>) => {
    setPendingAction(actionId);
    setError(null);
    setNotice(null);
    try {
      const message = await action();
      if (message) setNotice(message);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Professor workflow step failed.");
    } finally {
      setPendingAction(null);
    }
  }, []);

  return { error, notice, pendingAction, run, setError };
}
