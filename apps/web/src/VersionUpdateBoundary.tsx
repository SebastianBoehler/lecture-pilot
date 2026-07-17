import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

const CHECK_INTERVAL_MS = 5 * 60 * 1000;
const RELOAD_GUARD_KEY = "lecturepilot.update.reload-target";

type ActivityRegistration = (token: symbol, active: boolean) => void;
type VersionUpdateBoundaryProps = PropsWithChildren<{
  buildId?: string;
  checkIntervalMs?: number;
  loadBuildId?: () => Promise<string | null>;
  reload?: () => void;
}>;

const VersionUpdateActivityContext = createContext<ActivityRegistration | null>(null);

export function VersionUpdateBoundary({
  buildId = __LECTUREPILOT_BUILD_ID__,
  checkIntervalMs = CHECK_INTERVAL_MS,
  loadBuildId = requestLatestBuildId,
  reload = reloadPage,
  children,
}: VersionUpdateBoundaryProps) {
  const [busyTokens, setBusyTokens] = useState<Set<symbol>>(() => new Set());
  const registerActivity = useCallback<ActivityRegistration>((token, active) => {
    setBusyTokens((current) => {
      if (active === current.has(token)) return current;
      const next = new Set(current);
      if (active) next.add(token);
      else next.delete(token);
      return next;
    });
  }, []);
  const busy = busyTokens.size > 0;
  const update = useVersionUpdate({
    buildId,
    busy,
    checkIntervalMs,
    loadBuildId,
    reload,
  });

  return (
    <VersionUpdateActivityContext.Provider value={registerActivity}>
      {children}
      {update.available ? <VersionUpdateBar busy={busy} reload={update.reloadNow} /> : null}
    </VersionUpdateActivityContext.Provider>
  );
}

export function useVersionUpdateActivity(active: boolean) {
  const registerActivity = useContext(VersionUpdateActivityContext);
  const token = useRef(Symbol("version-update-activity"));

  useLayoutEffect(() => {
    if (!registerActivity) return;
    const activityToken = token.current;
    registerActivity(activityToken, active);
    return () => registerActivity(activityToken, false);
  }, [active, registerActivity]);
}

function useVersionUpdate({
  buildId,
  busy,
  checkIntervalMs,
  loadBuildId,
  reload,
}: {
  buildId: string;
  busy: boolean;
  checkIntervalMs: number;
  loadBuildId: () => Promise<string | null>;
  reload: () => void;
}) {
  const [availableBuildId, setAvailableBuildId] = useState<string | null>(null);
  const checkInFlight = useRef(false);
  const monitoringEnabled = buildId !== "development" && buildId !== "unknown";

  const checkForUpdate = useCallback(async () => {
    if (!monitoringEnabled || checkInFlight.current) return;
    checkInFlight.current = true;
    try {
      const latestBuildId = await loadBuildId();
      if (!latestBuildId) return;
      if (latestBuildId === buildId) {
        clearReloadGuard(latestBuildId);
        setAvailableBuildId(null);
      } else {
        setAvailableBuildId(latestBuildId);
      }
    } catch {
      // A later focus, visibility, or interval check will try again.
    } finally {
      checkInFlight.current = false;
    }
  }, [buildId, loadBuildId, monitoringEnabled]);

  useEffect(() => {
    if (!monitoringEnabled) return;
    void checkForUpdate();
    const handleFocus = () => void checkForUpdate();
    const handleVisibility = () => {
      if (document.visibilityState === "visible") void checkForUpdate();
    };
    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [checkForUpdate, monitoringEnabled]);

  useEffect(() => {
    if (!monitoringEnabled) return;
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") void checkForUpdate();
    }, checkIntervalMs);
    return () => window.clearInterval(intervalId);
  }, [checkForUpdate, checkIntervalMs, monitoringEnabled]);

  useEffect(() => {
    if (!availableBuildId || busy) return;
    if (readReloadGuard() === availableBuildId) return;
    writeReloadGuard(availableBuildId);
    reload();
  }, [availableBuildId, busy, reload]);

  return {
    available: availableBuildId !== null,
    reloadNow: () => {
      if (availableBuildId) writeReloadGuard(availableBuildId);
      reload();
    },
  };
}

function VersionUpdateBar({ busy, reload }: { busy: boolean; reload: () => void }) {
  const german = document.documentElement.lang.toLowerCase().startsWith("de");
  const message = german
    ? busy
      ? "Ein LecturePilot-Update ist bereit. Die Seite wird nach dem laufenden Vorgang neu geladen."
      : "LecturePilot wurde aktualisiert. Lade die Seite neu, um fortzufahren."
    : busy
      ? "A LecturePilot update is ready. The page will reload after the current task finishes."
      : "LecturePilot was updated. Reload the page to continue.";

  return (
    <aside className="version-update-bar" role="status" aria-live="polite">
      <span>{message}</span>
      <button type="button" onClick={reload}>
        {german ? "Jetzt neu laden" : "Reload now"}
      </button>
    </aside>
  );
}

async function requestLatestBuildId(): Promise<string | null> {
  const response = await fetch("/version.json", {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return null;
  const body: unknown = await response.json();
  if (!isVersionManifest(body)) return null;
  return body.buildId.trim() || null;
}

function isVersionManifest(value: unknown): value is { buildId: string } {
  return Boolean(
    value &&
    typeof value === "object" &&
    typeof (value as { buildId?: unknown }).buildId === "string",
  );
}

function reloadPage() {
  window.location.reload();
}

function readReloadGuard() {
  try {
    return window.sessionStorage.getItem(RELOAD_GUARD_KEY);
  } catch {
    return null;
  }
}

function writeReloadGuard(buildId: string) {
  try {
    window.sessionStorage.setItem(RELOAD_GUARD_KEY, buildId);
  } catch {
    // Storage can be unavailable in hardened browser modes; reload still works.
  }
}

function clearReloadGuard(currentBuildId: string) {
  try {
    if (window.sessionStorage.getItem(RELOAD_GUARD_KEY) === currentBuildId) {
      window.sessionStorage.removeItem(RELOAD_GUARD_KEY);
    }
  } catch {
    // No cleanup is needed when storage is unavailable.
  }
}
