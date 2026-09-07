import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { useProfessorPracticeDesignGate } from "./practiceDesignGate";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { LoginSession } from "./types";
import {
  getPracticeDesign,
  getPracticeDesignReadiness,
  proposePracticeDesign,
  PracticeDesignRequestError,
} from "./practiceDesignApi";

vi.mock("./practiceDesignApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./practiceDesignApi")>()),
  getPracticeDesign: vi.fn(),
  getPracticeDesignReadiness: vi.fn(),
  proposePracticeDesign: vi.fn(),
}));
const session = { username: "professor", tenant_id: "tenant" } as LoginSession;
const lectures = ["01", "02", "03", "04"].map((id) => ({
  id: `lecture-${id}`,
  label: `Lecture ${id}`,
}));
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getPracticeDesignReadiness).mockResolvedValue({ ready_for_generation: false } as never);
});

it("automatically prepares all missing plans after source confirmation, preserving existing plans", async () => {
  const existing = practiceDesignFixture({ lectureId: "lecture-01", approvedBy: "professor" });
  vi.mocked(getPracticeDesign).mockImplementation(async ({ lectureId }) => {
    if (lectureId === "lecture-01") return existing;
    throw new PracticeDesignRequestError("Missing", 404);
  });
  const finish = new Map<string, () => void>();
  vi.mocked(proposePracticeDesign).mockImplementation(
    ({ lectureId }) =>
      new Promise((resolve) => {
        finish.set(lectureId, () => resolve(practiceDesignFixture({ lectureId })));
      }),
  );
  const { result, rerender } = renderHook(
    ({ ready }) =>
      useProfessorPracticeDesignGate({
        courseId: "course",
        session,
        targetLectures: lectures,
        routingReady: ready,
      }),
    { initialProps: { ready: false } },
  );
  await waitFor(() => expect(getPracticeDesign).toHaveBeenCalledTimes(4));
  expect(proposePracticeDesign).not.toHaveBeenCalled();
  rerender({ ready: true });
  await waitFor(() => expect(proposePracticeDesign).toHaveBeenCalledTimes(3));
  expect(result.current.practiceDesignStep.preparing).toBe(true);
  expect(result.current.practiceDesignStep.designs["lecture-01"]).toEqual(existing);
  await act(async () => finish.get("lecture-02")!());
  await waitFor(() => expect(proposePracticeDesign).toHaveBeenCalledTimes(3));
  await act(async () => {
    finish.get("lecture-03")!();
    finish.get("lecture-04")!();
  });
  await waitFor(() => expect(result.current.practiceDesignStep.preparing).toBe(false));
  expect(Object.keys(result.current.practiceDesignStep.designs)).toHaveLength(4);
  expect(proposePracticeDesign).not.toHaveBeenCalledWith(
    expect.objectContaining({ lectureId: "lecture-01" }),
  );
});

it("shows a failed automatic proposal without repeatedly retrying it", async () => {
  vi.mocked(getPracticeDesign).mockRejectedValue(new PracticeDesignRequestError("Missing", 404));
  vi.mocked(proposePracticeDesign).mockRejectedValue(new Error("Source-backed proposal failed"));
  const { result, rerender } = renderHook(() =>
    useProfessorPracticeDesignGate({
      courseId: "course",
      session,
      targetLectures: lectures.slice(0, 1),
      routingReady: true,
    }),
  );
  await waitFor(() =>
    expect(result.current.practiceDesignStep.errorsByLecture["lecture-01"]).toBe(
      "Source-backed proposal failed",
    ),
  );
  expect(result.current.practiceDesignStep.preparing).toBe(false);
  rerender();
  expect(proposePracticeDesign).toHaveBeenCalledTimes(1);
});

it("does not propose a replacement when an existing plan's readiness lookup fails", async () => {
  vi.mocked(getPracticeDesign).mockResolvedValue(practiceDesignFixture());
  vi.mocked(getPracticeDesignReadiness).mockRejectedValue(
    new PracticeDesignRequestError("Readiness unavailable", 404),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesignGate({
      courseId: "course",
      session,
      targetLectures: lectures.slice(0, 1),
      routingReady: true,
    }),
  );
  await waitFor(() => expect(result.current.practiceDesignStep.preparing).toBe(false));
  expect(result.current.practiceDesignStep.errorsByLecture["lecture-01"]).toBe(
    "Readiness unavailable",
  );
  expect(proposePracticeDesign).not.toHaveBeenCalled();
  expect(result.current.practiceDesignStep.designs["lecture-01"]).toBeDefined();
  expect(result.current.designReady).toBe(false);
  vi.mocked(getPracticeDesignReadiness).mockResolvedValue({ ready_for_generation: false } as never);
  await act(async () => result.current.practiceDesignStep.onReload("lecture-01"));
  await waitFor(() =>
    expect(result.current.practiceDesignStep.errorsByLecture["lecture-01"]).toBeUndefined(),
  );
  expect(result.current.practiceDesignStep.error).toBeNull();
  expect(proposePracticeDesign).not.toHaveBeenCalled();
});
