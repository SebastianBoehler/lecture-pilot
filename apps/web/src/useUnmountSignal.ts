import { useEffect, useRef } from "react";

/** Returns a getter for an AbortSignal that fires when the component unmounts (e.g. logout). */
export function useUnmountSignal() {
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const owner = controller;
    // A remount (React strict mode) starts with a fresh controller instead of an aborted one.
    if (owner.current?.signal.aborted) owner.current = null;
    return () => owner.current?.abort();
  }, []);
  return () => (controller.current ??= new AbortController()).signal;
}
