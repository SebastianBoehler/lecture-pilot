const UNAUTHORIZED_EVENT = "lecturepilot:unauthorized";

/** A request was rejected because the session ended; the session hook re-checks it. */
export function reportUnauthorized() {
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

export function onUnauthorized(listener: () => void) {
  window.addEventListener(UNAUTHORIZED_EVENT, listener);
  return () => window.removeEventListener(UNAUTHORIZED_EVENT, listener);
}
