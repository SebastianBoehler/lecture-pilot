import { afterEach, expect, it, vi } from "vitest";

import { draftLectureCanvas } from "./canvasDraftApi";
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
