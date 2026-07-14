import { describe, expect, it, vi } from "vitest";

import {
  CanvasGenerationBatchError,
  describeCanvasGenerationError,
  generateLectureCanvasDrafts,
} from "./professorCanvasGeneration";
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

  it("reports successful drafts even when another lecture fails", async () => {
    const onDraftReady = vi.fn();
    const onProgress = vi.fn();

    await expect(
      generateLectureCanvasDrafts({
        draft: async (lectureId) => {
          if (lectureId === "lecture-02") throw new TypeError("Failed to fetch");
          return canvas;
        },
        lectureIds: ["lecture-01", "lecture-02"],
        onDraftReady,
        onProgress,
      }),
    ).rejects.toBeInstanceOf(CanvasGenerationBatchError);

    expect(onDraftReady).toHaveBeenCalledWith("lecture-01", canvas);
    expect(onProgress).toHaveBeenCalledWith(
      expect.objectContaining({
        lectureId: "lecture-02",
        status: "error",
        errorKind: "network",
      }),
    );
  });
});
