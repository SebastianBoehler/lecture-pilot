import { useCallback, useEffect, useState } from "react";

import { readAppRoute } from "./appRoute";

export function useAppRoute() {
  const [route, setRoute] = useState(() => readAppRoute(window.location));

  useEffect(() => {
    const handlePopState = () => setRoute(readAppRoute(window.location));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((path: string, options: { replace?: boolean } = {}) => {
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (current !== path) {
      window.history[options.replace ? "replaceState" : "pushState"]({}, "", path);
    }
    setRoute(readAppRoute(window.location));
  }, []);

  return { navigate, route };
}
