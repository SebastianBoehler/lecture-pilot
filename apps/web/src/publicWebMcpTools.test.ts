import { expect, it, vi } from "vitest";
import { createPublicWebMcpTools } from "./publicWebMcpTools";
import { howItWorksContent } from "./howItWorksContent";

function fixture() {
  const state = { locale: "en" as const, busy: false, navigate: vi.fn() };
  return { state, tools: createPublicWebMcpTools(() => state) };
}
it("returns the existing public guide without authentication or network access", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  const { tools } = fixture();
  const output = await tools[0].execute({ language: "de" });
  expect(output).toMatchObject({
    name: "LecturePilot",
    article: howItWorksContent.de,
    student_tools_require_authentication: true,
  });
  expect(fetch).not.toHaveBeenCalled();
});
it("restricts public requests to known guides and languages", async () => {
  const { tools, state } = fixture();
  await expect(tools[0].execute({ course_id: "private" })).rejects.toThrow(/Unexpected/);
  await expect(tools[0].execute({ language: "fr" })).rejects.toThrow(/Invalid/);
  await expect(tools[1].execute({ page: "/courses/private" })).rejects.toThrow(/Invalid/);
  expect(state.navigate).not.toHaveBeenCalled();
});
it("opens only public guides and respects active learning", async () => {
  const { tools, state } = fixture();
  await tools[1].execute({ page: "privacy" });
  expect(state.navigate).toHaveBeenCalledWith("/privacy");
  state.busy = true;
  await expect(tools[1].execute({ page: "how-it-works" })).rejects.toThrow(/student/);
  expect(state.navigate).toHaveBeenCalledTimes(1);
});
