import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { localDemoSession, localProfessorSession } from "./appDefaults";
import { useWebMcp } from "./useWebMcp";
import type { WebMcpState } from "./webMcpTools";
import type { WebMcpTool } from "./webMcpTypes";

const state: WebMcpState = {
  session: localDemoSession,
  theme: "light",
  locale: "en",
  busy: false,
  navigate: vi.fn(),
  openCourse: vi.fn(),
  setTheme: vi.fn(),
  setLocale: vi.fn(),
};
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
it("does not expose tools for logged-out or professor sessions", () => {
  const f = context();
  const hook = renderHook(useWebMcp, { initialProps: { ...state, session: null } as WebMcpState });
  hook.rerender({ ...state, session: localProfessorSession });
  expect(f.registerTool).not.toHaveBeenCalled();
});
it("uses current settings and revokes tools and saved callbacks on logout", async () => {
  const f = context();
  const hook = renderHook(useWebMcp, { initialProps: state });
  await waitFor(() => expect(f.registered.size).toBe(7));
  const tool = f.registered.get("lecturepilot_get_display_settings")!;
  hook.rerender({ ...state, theme: "dark" });
  await expect(tool.execute({})).resolves.toEqual({ theme: "dark", language: "en" });
  expect(f.registerTool).toHaveBeenCalledTimes(7);
  hook.rerender({ ...state, session: null });
  expect(f.registered.size).toBe(0);
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
  await waitFor(() => expect(f.registered.size).toBe(7));
  act(() => hook.unmount());
  expect(f.registered.size).toBe(0);
});
