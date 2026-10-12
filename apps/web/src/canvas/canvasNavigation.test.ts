import { afterEach, expect, it, vi } from "vitest";

import { scrollToCanvasAnchor } from "./canvasNavigation";

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

it("clears the measured preview banner when scrolling a section into view", () => {
  const main = document.createElement("section");
  main.className = "lesson-main";
  const banner = document.createElement("aside");
  banner.className = "professor-preview-banner";
  vi.spyOn(banner, "getBoundingClientRect").mockReturnValue({ height: 92 } as DOMRect);
  const anchor = document.createElement("section");
  anchor.id = "topic";
  anchor.className = "canvas-section";
  anchor.scrollIntoView = vi.fn();
  main.append(banner, anchor);
  document.body.append(main);

  scrollToCanvasAnchor("topic");
  expect(anchor.style.scrollMarginBlockStart).toBe("calc(var(--lesson-header-offset) + 112px)");
  expect(anchor.scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });

  banner.remove();
  scrollToCanvasAnchor("topic");
  expect(anchor.style.scrollMarginBlockStart).toBe("");
});
