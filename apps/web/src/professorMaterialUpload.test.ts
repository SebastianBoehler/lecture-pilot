import { afterEach, expect, it, vi } from "vitest";

import { uploadProfessorMaterials } from "./professorMaterialUpload";
import type { LoginSession } from "./types";

const session: LoginSession = {
  username: "professor-test",
  term: "Sommer 2026",
  courses: [],
  roles: ["professor"],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

it("bounds parallel material uploads and finalizes the source index once", async () => {
  let activeUploads = 0;
  let maxActiveUploads = 0;
  let releaseUpload: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => {
    releaseUpload = resolve;
  });
  const uploadBodies: FormData[] = [];
  let finalizeCalls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/source-bundle")) {
        finalizeCalls += 1;
        expect(activeUploads).toBe(0);
        return response({ course_id: "course", files: [], counts_by_kind: {} });
      }
      uploadBodies.push(init?.body as FormData);
      activeUploads += 1;
      maxActiveUploads = Math.max(maxActiveUploads, activeUploads);
      await gate;
      activeUploads -= 1;
      return response({ path: "uploaded.md", kind: "markdown", size_bytes: 1 });
    }),
  );

  const pending = uploadProfessorMaterials({
    courseId: "course",
    files: Array.from({ length: 9 }, (_, index) => new File([`${index}`], `${index}.md`)),
    session,
  });
  await vi.waitFor(() => expect(activeUploads).toBe(4));
  releaseUpload?.();
  const result = await pending;

  expect(result.error).toBeNull();
  expect(result.uploaded).toHaveLength(9);
  expect(result.ignored).toEqual([]);
  expect(maxActiveUploads).toBe(4);
  expect(finalizeCalls).toBe(1);
  expect(uploadBodies).toHaveLength(9);
  expect(uploadBodies.every((body) => body.get("refresh_index") === "false")).toBe(true);
});

it("keeps ignored-file UX and finalizes successful files before reporting a failure", async () => {
  let finalizeCalls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/source-bundle")) {
        finalizeCalls += 1;
        return response({ course_id: "course", files: [], counts_by_kind: {} });
      }
      const path = String((init?.body as FormData).get("path"));
      if (path.endsWith("ignored.aux")) {
        return response({ detail: "File type .aux is not writable." }, false);
      }
      if (path.endsWith("failed.md")) {
        return response({ detail: "The backend is unavailable." }, false);
      }
      return response({ path, kind: "markdown", size_bytes: 1 });
    }),
  );

  const result = await uploadProfessorMaterials({
    courseId: "course",
    files: [
      new File(["ok"], "ready.md"),
      new File(["skip"], "ignored.aux"),
      new File(["fail"], "failed.md"),
    ],
    session,
  });

  expect(result.uploaded.map((item) => item.path)).toEqual(["uploads/ready.md"]);
  expect(result.ignored).toEqual(["uploads/ignored.aux"]);
  expect(result.error?.message).toMatch(/uploads\/failed\.md: The backend is unavailable/);
  expect(finalizeCalls).toBe(1);
});

it("returns successful mutations when the final source refresh fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/source-bundle")) {
        return response({ detail: "Source index refresh failed." }, false);
      }
      const path = String((init?.body as FormData).get("path"));
      return response({ path, kind: "markdown", size_bytes: 1 });
    }),
  );

  const result = await uploadProfessorMaterials({
    courseId: "course",
    files: [new File(["ok"], "ready.md")],
    session,
  });

  expect(result.uploaded.map((item) => item.path)).toEqual(["uploads/ready.md"]);
  expect(result.bundle).toBeNull();
  expect(result.error?.message).toMatch(/source index refresh failed/i);
});

it("marks an upload mutation uncertain when its response is lost", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (String(url).includes("/source-bundle")) {
        return response({
          course_id: "course",
          counts_by_kind: { markdown: 1 },
          files: [{ path: "uploads/ready.md", kind: "markdown", size_bytes: 2 }],
        });
      }
      throw new TypeError("Failed to fetch");
    }),
  );

  const result = await uploadProfessorMaterials({
    courseId: "course",
    files: [new File(["ok"], "ready.md")],
    session,
  });

  expect(result.mutationUncertain).toBe(true);
  expect(result.uploaded).toEqual([]);
  expect(result.bundle?.files.map((file) => file.path)).toEqual(["uploads/ready.md"]);
  expect(result.error?.message).toMatch(/ready\.md.*failed to fetch/i);
});

it("preserves mutation uncertainty when upload and source refresh both fail", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (String(url).includes("/source-bundle")) {
        return response({ detail: "Source index refresh failed." }, false);
      }
      throw new TypeError("Failed to fetch");
    }),
  );

  const result = await uploadProfessorMaterials({
    courseId: "course",
    files: [new File(["ok"], "ready.md")],
    session,
  });

  expect(result.mutationUncertain).toBe(true);
  expect(result.uploaded).toEqual([]);
  expect(result.bundle).toBeNull();
  expect(result.error?.message).toMatch(/failed to fetch.*source.*refresh.*failed/i);
});

function response(payload: unknown, ok = true) {
  return { ok, json: async () => payload } as Response;
}
