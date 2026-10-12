import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NotesExportButton } from "./NotesExportButton";
import { renderWithI18n } from "../test/renderWithI18n";
import type { LoginSession } from "../shared/types";

afterEach(() => vi.unstubAllGlobals());

const session: LoginSession = {
  username: "student-a",
  term: "2026",
  roles: ["student"],
  courses: [],
};

describe("NotesExportButton", () => {
  it("downloads the learner's notes as a Markdown file", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(
      async () => new Response("# Notes\n", { headers: { "Content-Type": "text/markdown" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:notes");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderWithI18n(
      <NotesExportButton courseId="c1" lectureId="lecture-01" mode="learner" session={session} />,
    );

    await user.click(screen.getByRole("button", { name: "Export my notes" }));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/courses/c1/lectures/lecture-01/notes.md"),
      expect.any(Object),
    );
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    click.mockRestore();
  });

  it("shows the backend reason when there is nothing to export", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "You have no notes for this lecture yet." }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );
    renderWithI18n(
      <NotesExportButton courseId="c1" lectureId="lecture-01" mode="learner" session={session} />,
    );

    await user.click(screen.getByRole("button", { name: "Export my notes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You have no notes for this lecture yet.",
    );
  });
});
