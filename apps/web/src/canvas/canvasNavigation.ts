export function scrollToCanvasAnchor(id: string) {
  const anchor = document.getElementById(id);
  if (typeof anchor?.scrollIntoView !== "function") return;
  const isSection = anchor.classList.contains("canvas-section");
  if (isSection) {
    const banner = anchor.closest(".lesson-main")?.querySelector(".professor-preview-banner");
    anchor.style.scrollMarginBlockStart = banner
      ? `calc(var(--lesson-header-offset) + ${banner.getBoundingClientRect().height + 20}px)`
      : "";
  }
  const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  anchor.scrollIntoView({
    behavior: reducedMotion ? "instant" : "smooth",
    block: isSection ? "start" : "center",
  });
}
