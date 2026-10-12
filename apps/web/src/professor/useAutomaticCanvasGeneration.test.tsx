import { StrictMode } from "react";
import { renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useAutomaticCanvasGeneration } from "./useAutomaticCanvasGeneration";

it("waits for readiness and launches each saved revision once, including Strict Mode", () => {
  const start = vi.fn();
  const { rerender } = renderHook(useAutomaticCanvasGeneration, {
    initialProps: { revision: "course:revision-1", ready: false, start },
    wrapper: StrictMode,
  });
  expect(start).not.toHaveBeenCalled();
  rerender({ revision: "course:revision-1", ready: true, start });
  expect(start).toHaveBeenCalledTimes(1);
  rerender({ revision: "course:revision-1", ready: false, start });
  rerender({ revision: "course:revision-1", ready: true, start });
  expect(start).toHaveBeenCalledTimes(1);
  rerender({ revision: "course:revision-2", ready: true, start });
  expect(start).toHaveBeenCalledTimes(2);
});
