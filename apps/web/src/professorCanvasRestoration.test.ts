import { expect, it, vi } from "vitest";
import { getDraftLectureCanvas } from "./api";
import { restoreFullCourseCanvasDrafts } from "./professorCanvasRestoration";
import type { LoginSession } from "./types";

vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  getDraftLectureCanvas: vi.fn(),
}));

it("does not replace known generation results with failures when status retrieval loses connection", async () => {
  vi.mocked(getDraftLectureCanvas).mockRejectedValueOnce(new TypeError("Failed to fetch"));
  await expect(
    restoreFullCourseCanvasDrafts({
      courseId: "course",
      lectureIds: ["lecture-01"],
      session: {} as LoginSession,
    }),
  ).rejects.toThrow(
    "Could not load current draft status. Refresh workspace state to reconnect; saved drafts and running jobs are unchanged.",
  );
});

it("bounds full-course status reads while preserving lecture order", async () => {
  let active = 0;
  let peak = 0;
  vi.mocked(getDraftLectureCanvas).mockImplementation(async (_course, lecture) => {
    active += 1;
    peak = Math.max(peak, active);
    await new Promise((resolve) => setTimeout(resolve, 1));
    active -= 1;
    return { id: lecture } as Awaited<ReturnType<typeof getDraftLectureCanvas>>;
  });
  const lectureIds = Array.from({ length: 14 }, (_, i) => `lecture-${i}`);
  const result = await restoreFullCourseCanvasDrafts({
    courseId: "course",
    lectureIds,
    session: {} as LoginSession,
  });
  expect(peak).toBeLessThanOrEqual(4);
  expect(result.restored.map((item) => item.lectureId)).toEqual(lectureIds);
});
