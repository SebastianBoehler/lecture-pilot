import { useEffect, useState } from "react";

export const DEMO_TUTOR_WORKSPACE_STORAGE_KEY = "lecturepilot.demoTutorWorkspacePublished";

export function useDemoTutorWorkspace() {
  const [published, setPublished] = useState(readDemoTutorWorkspacePublished);

  useEffect(() => {
    function handleStorage(event: StorageEvent) {
      if (event.key === DEMO_TUTOR_WORKSPACE_STORAGE_KEY) {
        setPublished(event.newValue === "true");
      }
    }
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  function publish() {
    setDemoTutorWorkspacePublished(true);
    setPublished(true);
  }

  function unpublish() {
    setDemoTutorWorkspacePublished(false);
    setPublished(false);
  }

  return [published, publish, unpublish] as const;
}

export function readDemoTutorWorkspacePublished() {
  try {
    return window.localStorage.getItem(DEMO_TUTOR_WORKSPACE_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function setDemoTutorWorkspacePublished(published: boolean) {
  try {
    window.localStorage.setItem(DEMO_TUTOR_WORKSPACE_STORAGE_KEY, String(published));
  } catch {
    // Local storage can be disabled; the current tab still receives the state update.
  }
}
