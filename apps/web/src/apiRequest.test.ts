import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest, ApiRequestError } from "./apiRequest";
import { errorMessage } from "./errorMessage";
import type { LoginSession } from "./types";

const session: LoginSession = {
  username: "student01",
  term: "Sommer 2026",
  auth_transport: "cookie",
  csrf_token: "csrf-token-with-at-least-thirty-two-characters",
  courses: [],
};

function stubFetch(body: string | null, status: number) {
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
    return new Response(body, { status });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiRequest", () => {
  it("sends an authenticated request and returns the JSON body", async () => {
    const fetchMock = stubFetch(JSON.stringify({ ok: true }), 200);

    await expect(
      apiRequest<{ ok: boolean }>(session, "/me/thing", "Thing failed.", { method: "POST" }),
    ).resolves.toEqual({ ok: true });

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/me\/thing$/);
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(session.csrf_token);
  });

  it("returns null for an empty successful response", async () => {
    stubFetch(null, 204);

    await expect(apiRequest(session, "/me/thing", "Thing failed.")).resolves.toBeNull();
  });

  it("throws the backend detail with the response status", async () => {
    stubFetch(JSON.stringify({ detail: "Not yours." }), 403);

    const error = await apiRequest(session, "/me/thing", "Thing failed.").catch((e) => e);

    expect(error).toBeInstanceOf(ApiRequestError);
    expect(error).toMatchObject({ message: "Not yours.", status: 403 });
  });

  it("falls back to the given message when the error body is unreadable", async () => {
    stubFetch("<html>", 502);

    await expect(apiRequest(session, "/me/thing", "Thing failed.")).rejects.toThrow(
      "Thing failed.",
    );
  });
});

describe("errorMessage", () => {
  it("prefers the thrown error's message over the fallback", () => {
    expect(errorMessage(new Error("Exact."), "Fallback.")).toBe("Exact.");
    expect(errorMessage("not an error", "Fallback.")).toBe("Fallback.");
  });
});
