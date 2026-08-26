import { StrictMode, useEffect } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useProfessorSourceRouting } from "./useProfessorSourceRouting";
import type { CourseSourceRoutingManifest, LoginSession } from "./types";

const session: LoginSession = {
  account_type: "professor",
  courses: [],
  roles: ["professor"],
  term: "Sommer 2026",
  username: "professor-demo",
};

describe("useProfessorSourceRouting", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("does not let a delayed previous course grant stale authority after reset", async () => {
    const delayedA = deferred<Response>();
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("course-a/source-routing")) return delayedA.promise;
        if (url.includes("course-b/source-routing"))
          return Promise.resolve(response({ detail: "Source assignments changed." }, 409));
        throw new Error(`Unexpected request: ${url}`);
      }),
    );
    const { result } = renderHook(() => useProfessorSourceRouting(session));

    act(() => void result.current.load("course-a").catch(() => undefined));
    act(() => result.current.reset());
    await act(async () => delayedA.resolve(response(routing("course-a", "a"))));
    await act(async () => result.current.load("course-b").catch(() => undefined));

    expect(result.current.routing).toBeNull();
    expect(result.current.status).toBe("unavailable");
  });

  it("keeps the latest StrictMode routing load when responses resolve out of order", async () => {
    const first = deferred<Response>();
    const second = deferred<Response>();
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        calls += 1;
        return calls === 1 ? first.promise : second.promise;
      }),
    );
    const { result } = renderHook(() => useStrictModeRoutingLoad("course-a"), {
      wrapper: StrictMode,
    });

    await waitFor(() => expect(calls).toBe(2));
    await act(async () => second.resolve(response(routing("course-a", "new"))));
    await waitFor(() => expect(result.current.routing?.source_revision).toBe("new"));
    await act(async () => first.resolve(response(routing("course-a", "old"))));

    expect(result.current.routing?.source_revision).toBe("new");
  });
});

function useStrictModeRoutingLoad(courseId: string) {
  const routing = useProfessorSourceRouting(session);
  const { load } = routing;
  useEffect(() => {
    void load(courseId).catch(() => undefined);
  }, [courseId, load]);
  return routing;
}

function routing(courseId: string, revision: string): CourseSourceRoutingManifest {
  return {
    confirmed: true,
    course_id: courseId,
    routes: [
      {
        kind: "markdown",
        lecture_id: "lecture-01",
        path: "lecture-01.md",
        role: "lecture",
        sha256: "a".repeat(64),
      },
    ],
    source_revision: revision,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((onResolve) => {
    resolve = onResolve;
  });
  return { promise, resolve };
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}
