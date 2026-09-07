import { afterEach, expect, it, vi } from "vitest";

import { draftLectureCanvas, repairLectureCanvas } from "./canvasDraftApi";
import { LECTUREPILOT_CLIENT_CONTRACT } from "./authz";
import type { LoginSession } from "./types";

afterEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("reuses one idempotency key after a disconnect and clears it on success", async () => {
  const randomUUID = vi
    .spyOn(globalThis.crypto, "randomUUID")
    .mockReturnValueOnce("11111111-1111-4111-8111-111111111111")
    .mockReturnValueOnce("22222222-2222-4222-8222-222222222222");
  const fetchMock = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
    .mockResolvedValue(new Response(JSON.stringify(canvas), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(draftLectureCanvas("course-1", "lecture-01", session)).rejects.toThrow(
    "Failed to fetch",
  );
  await draftLectureCanvas("course-1", "lecture-01", session);
  await draftLectureCanvas("course-1", "lecture-01", session);

  const keys = fetchMock.mock.calls.map(([, init]) =>
    new Headers(init?.headers).get("idempotency-key"),
  );
  expect(keys).toEqual([
    "11111111-1111-4111-8111-111111111111",
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
  ]);
  expect(
    fetchMock.mock.calls.map(([, init]) =>
      new Headers(init?.headers).get("X-LecturePilot-Client-Contract"),
    ),
  ).toEqual([
    LECTUREPILOT_CLIENT_CONTRACT,
    LECTUREPILOT_CLIENT_CONTRACT,
    LECTUREPILOT_CLIENT_CONTRACT,
  ]);
  expect(randomUUID).toHaveBeenCalledTimes(2);
});

it("uses a new key after the server confirms a terminal generation failure", async () => {
  vi.spyOn(globalThis.crypto, "randomUUID")
    .mockReturnValueOnce("11111111-1111-4111-8111-111111111111")
    .mockReturnValueOnce("22222222-2222-4222-8222-222222222222");
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Generation failed." }), {
        status: 502,
        headers: { "X-Generation-Status": "failed" },
      }),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify(canvas), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(draftLectureCanvas("course-1", "lecture-01", session)).rejects.toThrow(
    "Generation failed.",
  );
  await draftLectureCanvas("course-1", "lecture-01", session);

  expect(
    fetchMock.mock.calls.map(([, init]) => new Headers(init?.headers).get("idempotency-key")),
  ).toEqual(["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"]);
});

it("uses a neutral error when the response has no usable API detail", async () => {
  vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("11111111-1111-4111-8111-111111111111");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 502 })));

  await expect(draftLectureCanvas("course-1", "lecture-01", session)).rejects.toThrow(
    "Canvas generation request failed.",
  );
});

it("sends AI repairs to the persisted repair endpoint", async () => {
  vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("11111111-1111-4111-8111-111111111111");
  const fetchMock = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(canvas), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await repairLectureCanvas("course-1", "lecture-01", session);

  expect(fetchMock.mock.calls[0]?.[0]).toContain(
    "/admin/courses/course-1/lectures/lecture-01/canvas/draft/repair",
  );
});

const session: LoginSession = {
  username: "professor01",
  email: "professor01@uni-tuebingen.de",
  term: "Sommer 2026",
  tenant_id: "tenant-tuebingen",
  roles: ["professor"],
  courses: [],
};

const canvas = {
  id: "course-1-lecture-01",
  course_id: "course-1",
  lecture_id: "lecture-01",
  title: "Canvas",
  source_kind: "generated",
  source_ref: "Lecture01.tex",
  workspace_path: "private/index.md",
  sections: [],
  warnings: [],
};

it("polls accepted jobs without holding a generation connection open", async () => {
  vi.useFakeTimers();
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "running" }), { status: 202 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "running" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "completed", canvas })));
  vi.stubGlobal("fetch", fetchMock);
  try {
    const result = draftLectureCanvas("course-1", "lecture-01", session);
    await vi.advanceTimersByTimeAsync(3000);
    await expect(result).resolves.toEqual(canvas);
    const firstHeaders = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(firstHeaders.get("Prefer")).toBe("respond-async");
    for (const [url, init] of fetchMock.mock.calls.slice(1)) {
      expect(url).toContain("/canvas/draft/status");
      expect(init.method).not.toBe("POST");
      expect(new Headers(init.headers).get("Idempotency-Key")).toBe(
        firstHeaders.get("Idempotency-Key"),
      );
    }
  } finally {
    vi.useRealTimers();
  }
});

it("preserves repairability and clears the request key for a failed polled job", async () => {
  vi.useFakeTimers();
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "running" }), { status: 202 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ status: "failed", error_detail: "Fix teaching", repairable: true }),
        ),
      ),
  );
  try {
    const result = draftLectureCanvas("course-1", "lecture-01", session);
    const assertion = expect(result).rejects.toMatchObject({
      message: "Fix teaching",
      terminalGeneration: true,
      repairable: true,
    });
    await vi.advanceTimersByTimeAsync(1500);
    await assertion;
    expect(
      window.sessionStorage.getItem("lecturepilot:canvas-generation:course-1:lecture-01:draft"),
    ).toBeNull();
  } finally {
    vi.useRealTimers();
  }
});
