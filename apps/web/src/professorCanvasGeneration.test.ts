import { describe, expect, it, vi } from "vitest";

import {
  CanvasGenerationBatchError,
  describeCanvasGenerationError,
  generateLectureCanvasDrafts,
} from "./professorCanvasGeneration";
import { CanvasDraftRequestError } from "./canvasDraftApi";
import type { CanvasDocument } from "./types";

const canvas = { id: "lecture-01-canvas" } as CanvasDocument;

describe("professor canvas generation", () => {
  it("distinguishes an unreadable network response from a service error", () => {
    expect(describeCanvasGenerationError(new TypeError("Failed to fetch"))).toEqual({
      errorKind: "network",
    });
    expect(describeCanvasGenerationError(new Error("Source reference is too long"))).toEqual({
      errorKind: "service",
      message: "Source reference is too long",
    });
  });

  it("marks a terminal source or validation failure as repairable", () => {
    expect(
      describeCanvasGenerationError(
        new CanvasDraftRequestError("Math block contains explanatory prose.", true, true),
      ),
    ).toEqual({
      errorKind: "repair",
      message: "Math block contains explanatory prose.",
    });
  });

  it("keeps non-repairable terminal failures as service errors", () => {
    expect(
      describeCanvasGenerationError(
        new CanvasDraftRequestError("Upload does not contain lecture material.", true),
      ),
    ).toEqual({
      errorKind: "service",
      message: "Upload does not contain lecture material.",
    });
  });

  it("reports successful drafts even when another lecture fails", async () => {
    vi.useFakeTimers();
    const onDraftReady = vi.fn();
    const onProgress = vi.fn();

    const generation = generateLectureCanvasDrafts({
      draft: async (lectureId) => {
        if (lectureId === "lecture-02") throw new TypeError("Failed to fetch");
        return canvas;
      },
      lectureIds: ["lecture-01", "lecture-02"],
      onDraftReady,
      onProgress,
    });
    const assertion = expect(generation).rejects.toBeInstanceOf(CanvasGenerationBatchError);
    await vi.runAllTimersAsync();
    await assertion;

    expect(onDraftReady).toHaveBeenCalledWith("lecture-01", canvas);
    expect(onProgress).toHaveBeenCalledWith(
      expect.objectContaining({
        lectureId: "lecture-02",
        status: "error",
        errorKind: "network",
      }),
    );
    vi.useRealTimers();
  });

  it("automatically reconnects a network failure through the same draft callback", async () => {
    vi.useFakeTimers();
    const draft = vi
      .fn<() => Promise<CanvasDocument>>()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(canvas);

    const generation = generateLectureCanvasDrafts({
      draft,
      lectureIds: ["lecture-01"],
    });
    await vi.runAllTimersAsync();

    await expect(generation).resolves.toEqual([canvas]);
    expect(draft).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});
