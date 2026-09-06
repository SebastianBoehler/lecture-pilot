import { useRef } from "react";
import { fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  LessonSidebarResize,
  sidebarWidthLimit,
  useLessonSidebarWidth,
} from "./LessonSidebarResize";
import { renderWithI18n } from "./test/renderWithI18n";

function Harness() {
  const layoutRef = useRef<HTMLElement>(null);
  const sidebar = useLessonSidebarWidth(layoutRef);
  return (
    <main ref={layoutRef} style={sidebar.style}>
      <LessonSidebarResize sidebar={sidebar} />
    </main>
  );
}
afterEach(() => vi.restoreAllMocks());

it("supports bounded keyboard resizing and restores default width", () => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    width: 1200,
  } as DOMRect);
  renderWithI18n(<Harness />);
  const handle = screen.getByRole("separator", { name: "Resize sidebar" });
  fireEvent.keyDown(handle, { key: "ArrowLeft" });
  expect(handle).toHaveAttribute("aria-valuenow", "456");
  fireEvent.keyDown(handle, { key: "End" });
  expect(handle).toHaveAttribute("aria-valuenow", "720");
  fireEvent.keyDown(handle, { key: "ArrowLeft" });
  expect(handle).toHaveAttribute("aria-valuenow", "720");
  fireEvent.keyDown(handle, { key: "Home" });
  fireEvent.keyDown(handle, { key: "ArrowRight" });
  expect(handle).toHaveAttribute("aria-valuenow", "376");
  fireEvent.doubleClick(handle);
  expect(handle).toHaveAttribute("aria-valuenow", "436");
});

it("reserves room for the canvas when the window narrows", () => {
  const bounds = vi
    .spyOn(HTMLElement.prototype, "getBoundingClientRect")
    .mockReturnValue({ width: 1200 } as DOMRect);
  renderWithI18n(<Harness />);
  const handle = screen.getByRole("separator");
  fireEvent.keyDown(handle, { key: "End" });
  bounds.mockReturnValue({ width: 900 } as DOMRect);
  fireEvent(window, new Event("resize"));
  expect(handle).toHaveAttribute("aria-valuemax", "500");
  expect(handle).toHaveAttribute("aria-valuenow", "500");
  expect(sidebarWidthLimit(861)).toBe(461);
});

it("drags the full sidebar and stops after pointer release", () => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    width: 1200,
  } as DOMRect);
  vi.stubGlobal("PointerEvent", MouseEvent);
  renderWithI18n(<Harness />);
  const handle = screen.getByRole("separator");
  handle.setPointerCapture = vi.fn();
  handle.hasPointerCapture = vi.fn(() => true);
  handle.releasePointerCapture = vi.fn();
  fireEvent.pointerDown(handle, { clientX: 800, button: 0 });
  fireEvent.pointerMove(handle, { clientX: 700 });
  expect(handle).toHaveAttribute("aria-valuenow", "536");
  fireEvent.pointerUp(handle);
  fireEvent.pointerMove(handle, { clientX: 600 });
  expect(handle).toHaveAttribute("aria-valuenow", "536");
  expect(handle.releasePointerCapture).toHaveBeenCalled();
  vi.unstubAllGlobals();
});
