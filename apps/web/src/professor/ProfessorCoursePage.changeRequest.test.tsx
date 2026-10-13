import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { calls, json, lecture, mockApi, renderCoursePage, states } from "./coursePageTestFixtures";

afterEach(() => vi.unstubAllGlobals());

const CHANGE = "/admin/courses/machine-learning/lectures/lecture-02/canvas/change-request";
const options = {
  base: "published",
  sections: [
    { id: "learning-update", title: "The update rule" },
    { id: "learning-momentum", title: "Momentum" },
  ],
  latest: null,
};

describe("Course page change requests", () => {
  it("requests a change limited to chosen sections and shows the lecture generating", async () => {
    let current = states([lecture("lecture-01"), lecture("lecture-02")]);
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(current),
      [`GET ${CHANGE}`]: () => json(options),
      [`POST ${CHANGE}`]: () => {
        current = states([
          lecture("lecture-01"),
          lecture("lecture-02", { draft: "generating", next_action: "wait" }),
        ]);
        return json({ status: "running" }, 202);
      },
    });
    const user = userEvent.setup();
    renderCoursePage();

    await user.click(await screen.findByRole("button", { name: "Request a change: Lecture 02" }));
    const dialog = await screen.findByRole("dialog", { name: "Request a change" });
    const submit = within(dialog).getByRole("button", { name: "Request change" });
    expect(submit).toBeDisabled();
    await user.type(
      within(dialog).getByLabelText("What should change?"),
      "  Add a worked example on momentum after the update rule.",
    );
    await user.click(await within(dialog).findByRole("checkbox", { name: "Momentum" }));
    await user.click(submit);

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const [[, init]] = calls(fetchMock, "POST", CHANGE);
    expect(JSON.parse(String(init?.body))).toEqual({
      instruction: "Add a worked example on momentum after the update rule.",
      section_ids: ["learning-momentum"],
    });
    const headers = new Headers(init?.headers);
    expect(headers.get("Prefer")).toBe("respond-async");
    expect(headers.get("Idempotency-Key")).toBeTruthy();
    expect(await screen.findByText("Generating draft…")).toBeInTheDocument();
  });

  it("shows the backend detail inline when a change cannot be requested", async () => {
    mockApi({
      "GET /lecture-states": () => json(states([lecture("lecture-02")])),
      [`GET ${CHANGE}`]: () => json(options),
      [`POST ${CHANGE}`]: () =>
        json({ detail: "A draft is already being generated for this lecture." }, 409),
    });
    const user = userEvent.setup();
    renderCoursePage();

    await user.click(await screen.findByRole("button", { name: "Request a change: Lecture 02" }));
    const dialog = await screen.findByRole("dialog", { name: "Request a change" });
    await user.type(within(dialog).getByLabelText("What should change?"), "Fix the sign.");
    await user.click(within(dialog).getByRole("button", { name: "Request change" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "A draft is already being generated for this lecture.",
    );
    expect(within(dialog).getByRole("button", { name: "Request change" })).toBeEnabled();
  });

  it("explains an unavailable lecture and keeps submit disabled", async () => {
    mockApi({
      "GET /lecture-states": () => json(states([lecture("lecture-02", { draft: "ready" })])),
      [`GET ${CHANGE}`]: () => json({ detail: "Generate a draft first." }, 409),
    });
    const user = userEvent.setup();
    renderCoursePage();

    await user.click(await screen.findByRole("button", { name: "Request a change: Lecture 02" }));
    const dialog = await screen.findByRole("dialog", { name: "Request a change" });
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Generate a draft first.");
    await user.type(within(dialog).getByLabelText("What should change?"), "Fix the sign.");
    expect(within(dialog).getByRole("button", { name: "Request change" })).toBeDisabled();
  });

  it("offers changes only for current drafts and publications and shows a later failure", async () => {
    mockApi({
      "GET /lecture-states": () =>
        json(
          states([
            lecture("lecture-01", {
              draft_error: "This change would alter an approved checkpoint.",
            }),
            lecture("lecture-02", {
              goals: "stale",
              draft: "none",
              next_action: "keep_or_regenerate_goals",
            }),
          ]),
        ),
    });
    renderCoursePage();

    expect(
      await screen.findByText(
        "Last change failed: This change would alter an approved checkpoint.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request a change: Lecture 01" })).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Request a change: Lecture 02" }),
    ).not.toBeInTheDocument();
  });
});
