import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { localDemoSession, localProfessorSession } from "./appDefaults";
import { useWebMcp } from "./useWebMcp";
import type { WebMcpState } from "./webMcpTools";
import type { WebMcpTool } from "./webMcpTypes";

const authenticatedStudent = { ...localDemoSession, auth_transport: "cookie" as const };

const state: WebMcpState = {
  session: authenticatedStudent,
  theme: "light",
  locale: "en",
  busy: false,
  navigate: vi.fn(),
  openCourse: vi.fn(),
  setTheme: vi.fn(),
  setLocale: vi.fn(),
};
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => authenticatedStudent }),
  );
});
afterEach(() => {
  Reflect.deleteProperty(document, "modelContext");
});

function context() {
  const registered = new Map<string, WebMcpTool>();
  const registerTool = vi.fn(async (tool: WebMcpTool, { signal }: { signal: AbortSignal }) => {
    if (signal.aborted) return;
    registered.set(tool.name, tool);
    signal.addEventListener("abort", () => registered.delete(tool.name));
  });
  Object.defineProperty(document, "modelContext", { configurable: true, value: { registerTool } });
  return { registered, registerTool };
}

it("does nothing in browsers without WebMCP", () => {
  expect(renderHook(() => useWebMcp(state)).result.current).toBeNull();
});
it("exposes only public tools for logged-out and professor sessions", async () => {
  const f = context();
  const hook = renderHook(useWebMcp, { initialProps: { ...state, session: null } as WebMcpState });
  await waitFor(() => expect(f.registered.size).toBe(2));
  expect([...f.registered.keys()]).toEqual([
    "lecturepilot_get_public_information",
    "lecturepilot_open_public_page",
  ]);
  hook.rerender({ ...state, session: localDemoSession });
  await waitFor(() => expect(f.registered.size).toBe(2));
  hook.rerender({ ...state, session: localProfessorSession });
  await waitFor(() => expect(f.registered.size).toBe(2));
  expect(f.registered.has("lecturepilot_list_courses")).toBe(false);
});
it("uses current settings and revokes tools and saved callbacks on logout", async () => {
  const f = context();
  const hook = renderHook(useWebMcp, { initialProps: state });
  await waitFor(() => expect(f.registered.size).toBe(9));
  const tool = f.registered.get("lecturepilot_get_display_settings")!;
  hook.rerender({ ...state, theme: "dark" });
  await expect(tool.execute({})).resolves.toEqual({ theme: "dark", language: "en" });
  expect(f.registerTool).toHaveBeenCalledTimes(9);
  hook.rerender({ ...state, session: null });
  await waitFor(() => expect(f.registered.size).toBe(2));
  await expect(tool.execute({})).rejects.toThrow(/session/);
});
it("removes partial registrations and reports registration failure", async () => {
  const f = context();
  f.registerTool.mockRejectedValueOnce(new Error("Unsupported API"));
  const hook = renderHook(() => useWebMcp(state));
  await waitFor(() => expect(hook.result.current).toMatch(/could not be registered/));
  expect(f.registered.size).toBe(0);
});
it("removes registrations on unmount", async () => {
  const f = context();
  const hook = renderHook(() => useWebMcp(state));
  await waitFor(() => expect(f.registered.size).toBe(9));
  act(() => hook.unmount());
  expect(f.registered.size).toBe(0);
});
