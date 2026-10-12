import { useEffect, useEffectEvent, useRef } from "react";

export function useAutomaticCanvasGeneration({
  revision,
  ready,
  start,
}: {
  revision: string;
  ready: boolean;
  start: () => void;
}) {
  const launched = useRef(new Set<string>());
  const begin = useEffectEvent(start);
  useEffect(() => {
    if (!ready || launched.current.has(revision)) return;
    launched.current.add(revision);
    begin();
  }, [ready, revision]);
}
