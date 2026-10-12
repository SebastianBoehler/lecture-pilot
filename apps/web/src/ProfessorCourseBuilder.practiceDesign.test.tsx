import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { builderSteps } from "./ProfessorBuilderStepper";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("practice-design builder blocking", () => {
  it("places learning plans between sources and media and blocks generation until every plan is approved", () => {
    const blocked = builderSteps({
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      designReady: false,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: true,
      routingReady: true,
      workspacePublished: false,
    });
    const ready = builderSteps({
      ...Object.fromEntries(blocked.map((step) => [step.id, step.ready])),
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      designReady: true,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: true,
      routingReady: true,
      workspacePublished: false,
    });

    expect(blocked.map((step) => step.id)).toEqual([
      "define",
      "upload",
      "sources",
      "design",
      "review",
      "generate",
      "publish",
    ]);
    expect(blocked.find((step) => step.id === "review")?.available).toBe(true);
    expect(blocked.find((step) => step.id === "generate")?.available).toBe(false);
    expect(ready.find((step) => step.id === "generate")?.available).toBe(true);
  });
});

afterEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("rejects a practice proposal without current confirmed lecture evidence", async () => {
  const fetchMock = professorFetchMock();
  const routingResponse = await fetchMock("/admin/courses/demo-ml-course/source-routing");
  const routing = await routingResponse.json();
  await fetchMock("/admin/courses/demo-ml-course/source-routing", {
    body: JSON.stringify(routing),
    method: "PUT",
  });

  const proposal = await fetchMock(
    "/admin/courses/demo-ml-course/lectures/lecture-02/practice-design/proposal",
    { method: "POST" },
  );
  expect(proposal.ok).toBe(false);
  expect(proposal.status).toBe(409);
});

it("drafts each approved plan while others are reviewed and keeps a stale approval conflict visible", async () => {
  const user = userEvent.setup();
  const fetchMock = professorFetchMock({ staleApprovalOnceFor: "lecture-02" });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);

  await openProfessorDemo(user);
  await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
  await user.click(screen.getByRole("button", { name: /create course workspace/i }));
  await user.upload(
    await screen.findByLabelText(/^choose files$/i),
    new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
  );
  await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
  await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));
  await user.click(await screen.findByText(/review source assignments/i));
  expect(await screen.findByLabelText(/route lecture01-eng\.tex/i)).toHaveValue("lecture");
  expect(screen.getByLabelText(/route lecture02-eng\.tex/i)).toHaveValue("lecture");
  expect(screen.queryByLabelText(/route lecture03-eng\.tex/i)).not.toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: /accept assignments and continue/i }));
  await user.click(
    await screen.findByRole("button", { name: /continue (?:without videos|to learning plan)/i }),
  );

  const navigation = await screen.findByRole("navigation", { name: "Learning plan lectures" });
  await user.click(await screen.findByRole("button", { name: /^approve learning goals$/i }));
  // Approval advances to the next open lecture.
  expect(await screen.findByRole("heading", { name: /02 · lecture 02/i })).toBeVisible();

  await user.click(within(navigation).getAllByRole("button")[0]);
  await screen.findByRole("heading", { name: /01 · lecture 01/i });
  await user.click(screen.getByRole("button", { name: /edit learning goals/i }));
  const outcome = screen.getByRole("textbox", { name: /outcome for posterior/i });
  await user.clear(outcome);
  await user.type(outcome, "Calculate a revised posterior from evidence.");
  await user.click(screen.getByRole("button", { name: /save learning plan/i }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /^approve learning goals$/i })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: /^approve learning goals$/i }));
  expect(await screen.findByRole("heading", { name: /02 · lecture 02/i })).toBeVisible();

  await user.click(screen.getByRole("button", { name: /^approve learning goals$/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/revision changed/i);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /^approve learning goals$/i })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: /^approve learning goals$/i }));
  const approvalRevisions = fetchMock.mock.calls
    .filter(
      ([url, init]) =>
        String(url).includes("lecture-02/practice-design/intent/approve") &&
        init?.method === "POST",
    )
    .map(([, init]) => JSON.parse(String(init?.body)).practice_design_revision);
  expect(approvalRevisions).toEqual(["d".repeat(64), "f".repeat(64)]);
  expect(await screen.findByText(/2 lecture canvases ready to review/i)).toBeInTheDocument();
  // Lecture 01 drafts again after its approved plan changed; lecture 02 drafts once.
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.filter(
        ([url, init]) => String(url).endsWith("/canvas/draft") && init?.method === "POST",
      ),
    ).toHaveLength(3),
  );
});

it("marks an approved design stale after a source update removes current routing", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", professorFetchMock({ staleRoutingAfterApproval: true }));
  render(<App />);

  await openProfessorDemo(user);
  await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
  await user.click(screen.getByRole("button", { name: /create course workspace/i }));
  await user.upload(
    await screen.findByLabelText(/^choose files$/i),
    new File(["# lecture three"], "Lecture03-eng.tex", { type: "application/x-tex" }),
  );
  await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
  await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));
  await screen.findByRole("heading", { name: /source assignments ready/i });
  await user.click(screen.getByText(/review source assignments/i));
  await user.click(await screen.findByRole("button", { name: /accept assignments and continue/i }));
  await user.click(
    await screen.findByRole("button", { name: /continue (?:without videos|to learning plan)/i }),
  );
  await user.click(await screen.findByRole("button", { name: /^approve learning goals$/i }));
  // The approved lecture starts drafting at once and discovers the changed routing.
  expect(await screen.findByText(/source assignments changed/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /learning plan/i }));
  expect((await screen.findAllByText(/reconfirm source routing/i))[0]).toBeVisible();
  expect(screen.queryByText(/learning goals approved/i)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^approve learning goals$/i })).toBeDisabled();
});

it("continues to media when the backend accepts a non-destructive source assignment", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", professorFetchMock({ autoConfirmRouting: true }));
  render(<App />);

  await openProfessorDemo(user);
  await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
  await user.click(screen.getByRole("button", { name: /create course workspace/i }));
  await user.upload(
    await screen.findByLabelText(/^choose files$/i),
    new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
  );
  await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
  await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));

  expect(await screen.findByText(/accepted automatically/i)).toBeInTheDocument();
  expect(
    await screen.findByRole("button", { name: /continue (?:without videos|to learning plan)/i }),
  ).toBeInTheDocument();
  // The accepted assignment stays reviewable under Materials.
  await user.click(screen.getByRole("button", { name: /02 materials/i }));
  await user.click(await screen.findByText(/review source assignments/i));
  expect(await screen.findByLabelText(/route lecture01-eng\.tex/i)).toHaveValue("lecture");
});
