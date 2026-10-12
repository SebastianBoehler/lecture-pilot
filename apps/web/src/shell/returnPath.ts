const returnPathKey = "lecturepilot.return-path";

/** Remember where to continue after (re-)login, e.g. a shared course link or the builder. */
export function rememberReturnPath(path: string) {
  try {
    window.sessionStorage.setItem(returnPathKey, path);
  } catch {}
}

export function takeReturnPath(): string | null {
  try {
    const path = window.sessionStorage.getItem(returnPathKey);
    window.sessionStorage.removeItem(returnPathKey);
    // Same-origin app paths only; never follow protocol-relative or external targets.
    return path && path.startsWith("/") && !path.startsWith("//") && path !== "/" ? path : null;
  } catch {
    return null;
  }
}
