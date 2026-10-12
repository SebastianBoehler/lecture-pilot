import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { useStoredLoginSession } from "./loginSessionStorage";
import { reportUnauthorized } from "../shared/sessionSignals";
import { rememberReturnPath, takeReturnPath } from "../shell/returnPath";

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

it("detects a cookie session that expires while the app stays open", async () => {
  window.localStorage.setItem(
    "lecturepilot.loginSession",
    JSON.stringify({ username: "prof", term: "WS", courses: [], auth_transport: "cookie" }),
  );
  let status = 200;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      status === 200
        ? Response.json({ username: "prof", courses: [] })
        : Response.json({ detail: "Session has expired." }, { status }),
    ),
  );
  const { result } = renderHook(() => useStoredLoginSession());
  await waitFor(() => expect(result.current[2]).toBe(false));
  expect(result.current[3]).toBe(false);

  status = 401;
  act(() => {
    window.dispatchEvent(new Event("focus"));
  });
  await waitFor(() => expect(result.current[3]).toBe(true));
  expect(result.current[0]).not.toBeNull();
});

it("checks the session as soon as a request reports it is no longer signed in", async () => {
  window.localStorage.setItem(
    "lecturepilot.loginSession",
    JSON.stringify({ username: "student", term: "WS", courses: [], auth_transport: "cookie" }),
  );
  let status = 200;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      status === 200
        ? Response.json({ username: "student", courses: [] })
        : Response.json({ detail: "Session is invalid or revoked." }, { status }),
    ),
  );
  const { result } = renderHook(() => useStoredLoginSession());
  await waitFor(() => expect(result.current[2]).toBe(false));

  status = 401;
  act(() => reportUnauthorized());
  await waitFor(() => expect(result.current[3]).toBe(true));
});

it("only returns same-origin app paths after login", () => {
  rememberReturnPath("/professor/courses/new");
  expect(takeReturnPath()).toBe("/professor/courses/new");
  expect(takeReturnPath()).toBeNull();
  rememberReturnPath("//evil.example/path");
  expect(takeReturnPath()).toBeNull();
});
