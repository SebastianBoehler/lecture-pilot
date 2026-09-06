import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { PracticeAttemptHistory } from "./PracticeAttemptHistory";
import { renderWithI18n } from "./test/renderWithI18n";

it("loads saved answers on demand and deletes only the selected attempt", async () => {
  const record = {
    id: "attempt-a",
    created_at: "2026-09-06T10:00:00Z",
    answers: { q: { text: "Saved reasoning" } },
  };
  let deleted = false;
  const fetcher = vi.fn(async (_url, init) => {
    if (init.method === "DELETE") deleted = true;
    return new Response(JSON.stringify(deleted ? [] : [record]), { status: 200 });
  });
  vi.stubGlobal("fetch", fetcher);
  const onReview = vi.fn();
  const onDelete = vi.fn();
  const user = userEvent.setup();
  renderWithI18n(
    <PracticeAttemptHistory
      courseId="course"
      examId="exam"
      disabled={false}
      session={{ username: "student", term: "", roles: ["student"], courses: [] }}
      onReview={onReview}
      onDelete={onDelete}
    />,
  );
  expect(fetcher).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Saved attempts" }));
  await user.click(await screen.findByRole("button", { name: "Review" }));
  expect(onReview).toHaveBeenCalledWith(record);
  await user.click(screen.getByRole("button", { name: "Delete attempt" }));
  expect(await screen.findByText("No saved attempts yet.")).toBeInTheDocument();
  expect(onDelete).toHaveBeenCalledWith("attempt-a");
  expect(fetcher.mock.calls[1][0]).toContain("/attempts/attempt-a");
});
