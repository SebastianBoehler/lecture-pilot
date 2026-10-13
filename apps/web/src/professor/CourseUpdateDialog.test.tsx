import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { calls, json, lecture, mockApi, renderCoursePage, states } from "./coursePageTestFixtures";

afterEach(() => vi.unstubAllGlobals());

const analysis = {
  course_id: "machine-learning",
  update_id: "update-1",
  candidates: [
    {
      candidate_id: "update:lecture-02",
      action: "update",
      lecture_id: "lecture-02",
      number: "02",
      title: "Gradient Descent",
      date: "2026-10-08",
      file_paths: ["Lecture02.tex", "figures/descent.pdf"],
    },
    {
      candidate_id: "new:3",
      action: "new",
      lecture_id: null,
      number: "03",
      title: "Lecture03",
      date: "2026-10-15",
      file_paths: ["Lecture03.tex"],
    },
  ],
  existing_lectures: [
    { lecture_id: "lecture-01", number: "01", title: "Introduction", date: "2026-10-01" },
    { lecture_id: "lecture-02", number: "02", title: "Gradient Descent", date: "2026-10-08" },
  ],
  unassigned_files: [
    { path: "notation.pdf", kind: "pdf", size_bytes: 10, sha256: "x", status: "new" },
  ],
  unchanged_files: 14,
};

describe("Upload changed materials", () => {
  it("compares, reviews and applies an update without starting drafts", async () => {
    let current = states([lecture("lecture-01"), lecture("lecture-02")]);
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(current),
      "POST /machine-learning/updates": () =>
        json({ course_id: "machine-learning", update_id: "update-1" }),
      "POST /updates/update-1/materials": () => json({ path: "x", kind: "latex", size_bytes: 1 }),
      "GET /updates/update-1": () => json(analysis),
      "POST /updates/update-1/apply": (init) => {
        current = states([
          lecture("lecture-01"),
          lecture("lecture-02", {
            sources: "changed",
            goals: "stale",
            next_action: "keep_or_regenerate_goals",
          }),
          lecture("lecture-03", {
            title: "Regularization",
            published: false,
            sources: "new",
            goals: "proposing",
            draft: "none",
            next_action: "wait",
          }),
        ]);
        return json({ ...JSON.parse(String(init?.body)), applied_files: 4 });
      },
    });
    const user = userEvent.setup();
    const props = renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Upload changed materials" }));
    const dialog = screen.getByRole("dialog", { name: "Upload changed materials" });
    expect(within(dialog).getByRole("button", { name: "Compare" })).toBeDisabled();
    await user.upload(within(dialog).getByLabelText("Choose files"), [
      new File(["a"], "Lecture02.tex"),
      new File(["b"], "Lecture03.tex"),
    ]);
    await user.click(within(dialog).getByRole("button", { name: "Compare" }));

    expect(await within(dialog).findByText("Changed lectures")).toBeInTheDocument();
    expect(within(dialog).getByText("Unchanged")).toBeInTheDocument();
    expect(within(dialog).getByText("2 files")).toBeInTheDocument();
    const title = within(dialog).getByRole("textbox", { name: "Title" });
    await user.clear(title);
    await user.type(title, "Regularization");
    await user.selectOptions(
      within(dialog).getByRole("combobox", { name: "Use notation.pdf for" }),
      "All lectures",
    );
    await user.click(within(dialog).getByRole("button", { name: "Apply update" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const body = JSON.parse(String(calls(fetchMock, "POST", "/apply")[0][1]?.body));
    expect(body.lectures).toEqual([
      expect.objectContaining({
        lecture_id: "lecture-02",
        file_paths: ["Lecture02.tex", "figures/descent.pdf", "notation.pdf"],
      }),
      expect.objectContaining({ lecture_id: null, number: "03", title: "Regularization" }),
      expect.objectContaining({ lecture_id: "lecture-01", file_paths: ["notation.pdf"] }),
    ]);
    expect(await screen.findByText("Proposing goals…")).toBeInTheDocument();
    expect(screen.getByText("Sources changed")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/canvas/draft"))).toBe(false);
    expect(props.onCourseChanged).toHaveBeenCalled();
  });

  it("explains a failed comparison and discards the staged update on cancel", async () => {
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(states([lecture("lecture-01")])),
      "POST /machine-learning/updates": () =>
        json({ course_id: "machine-learning", update_id: "update-2" }),
      "POST /updates/update-2/materials": () =>
        json({ detail: "This course has reached its storage quota." }, 507),
      "DELETE /updates/update-2": () => json(null),
    });
    const user = userEvent.setup();
    renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Upload changed materials" }));
    const dialog = screen.getByRole("dialog");
    await user.upload(within(dialog).getByLabelText("Choose files"), new File(["a"], "big.pdf"));
    await user.click(within(dialog).getByRole("button", { name: "Compare" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "This course has reached its storage quota.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(calls(fetchMock, "DELETE", "/updates/update-2")).toHaveLength(1));
  });
});
