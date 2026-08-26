import { render, screen, waitFor } from "@testing-library/react";
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

it("requires every full-course plan approval and keeps a stale approval conflict visible", async () => {
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

  const proposals = await screen.findAllByRole("button", { name: /generate learning plan/i });
  await user.click(proposals[0]);
  await user.click(proposals[1]);
  await waitFor(() =>
    expect(screen.getAllByRole("button", { name: /approve learning plan/i })).toHaveLength(2),
  );
  await user.click(screen.getAllByRole("button", { name: /approve learning plan/i })[0]);
  await waitFor(() =>
    expect(screen.getAllByRole("button", { name: /approve learning plan/i })).toHaveLength(1),
  );
  expect(screen.getByRole("button", { name: /06 generate/i })).toBeDisabled();

  const details = screen.getAllByText(/edit target details/i)[0].closest("details");
  await user.click(details!.querySelector("summary")!);
  const outcome = screen.getAllByLabelText(/outcome for posterior/i)[0];
  await user.clear(outcome);
  await user.type(outcome, "Calculate a revised posterior from evidence.");
  await user.click(screen.getAllByRole("button", { name: /save learning plan/i })[0]);
  await waitFor(() =>
    expect(screen.getAllByRole("button", { name: /approve learning plan/i })).toHaveLength(2),
  );
  expect(screen.getByRole("button", { name: /06 generate/i })).toBeDisabled();
  await user.click(screen.getAllByRole("button", { name: /approve learning plan/i })[0]);
  await waitFor(() =>
    expect(screen.getAllByRole("button", { name: /approve learning plan/i })).toHaveLength(1),
  );

  await user.click(screen.getByRole("button", { name: /approve learning plan/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/revision changed/i);
  expect(screen.getByRole("button", { name: /approve learning plan/i })).toBeEnabled();

  await user.click(screen.getByRole("button", { name: /approve learning plan/i }));
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: /approve learning plan/i }),
    ).not.toBeInTheDocument(),
  );
  const approvalRevisions = fetchMock.mock.calls
    .filter(
      ([url, init]) =>
        String(url).includes("lecture-02/practice-design/approve") && init?.method === "POST",
    )
    .map(([, init]) => JSON.parse(String(init?.body)).practice_design_revision);
  expect(approvalRevisions).toEqual(["d".repeat(64), "f".repeat(64)]);
  await user.click(screen.getByRole("button", { name: /05 media/i }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /continue to canvas draft/i })).toBeEnabled(),
  );
});
