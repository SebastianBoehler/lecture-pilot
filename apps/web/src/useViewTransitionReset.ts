import { useEffect } from "react";

import type { View } from "./types";

export function useViewTransitionReset(view: View) {
  useEffect(() => {
    if (window.scrollX !== 0 || window.scrollY !== 0) {
      window.scrollTo({ behavior: "auto", left: 0, top: 0 });
    }

    const focusHeading = () => {
      const heading = document.querySelector<HTMLElement>("main h1, [role='main'] h1");
      if (!heading) return false;
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
      return true;
    };

    if (focusHeading()) return undefined;

    const observer = new MutationObserver(() => {
      if (focusHeading()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    const timeout = window.setTimeout(() => observer.disconnect(), 1_000);
    return () => {
      observer.disconnect();
      window.clearTimeout(timeout);
    };
  }, [view]);
}
