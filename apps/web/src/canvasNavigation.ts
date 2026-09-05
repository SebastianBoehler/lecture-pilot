export function scrollToCanvasAnchor(id: string) {
  const anchor = document.getElementById(id);
  if (typeof anchor?.scrollIntoView !== "function") return;
  const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  anchor.scrollIntoView({
    behavior: reducedMotion ? "instant" : "smooth",
    block: anchor.classList.contains("canvas-section") ? "start" : "center",
  });
}
