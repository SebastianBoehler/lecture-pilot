import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { localProfessorSession } from "../shell/appDefaults";
import { walkthroughStorageKey } from "../professor/professorWalkthroughState";

export async function showAllPublishedLectures(user: ReturnType<typeof userEvent.setup>) {
  if (screen.queryByRole("button", { name: /open lecture 03/i })) return;
  const showAll = screen.queryByRole("button", { name: /show all/i });
  const toggle = showAll ?? (await screen.findByRole("button", { name: /show all/i }));
  await user.click(toggle);
}

export async function openLecture03FromDashboard(
  user: ReturnType<typeof userEvent.setup>,
  waitForState = true,
) {
  await showAllPublishedLectures(user);
  await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
  // Allow the cold lazy lesson module to transform on constrained CI workers.
  if (waitForState) await screen.findByLabelText(/close tutor chat/i, {}, { timeout: 5_000 });
  else await screen.findByText("Checking your saved attempt before opening the lecture…");
}

export async function openProfessorDemo(user: ReturnType<typeof userEvent.setup>) {
  // The lazily loaded first-visit tour would otherwise take focus at an arbitrary point.
  window.localStorage.setItem(walkthroughStorageKey(localProfessorSession.username), "seen");
  await user.click(screen.getByRole("button", { name: /preview professor account/i }));
  // Professors with courses land on course management; the builder is one header click away.
  await user.click(await screen.findByRole("button", { name: /^course builder$/i }));
  await screen.findByRole("navigation", { name: /course builder progress/i }, { timeout: 5_000 });
}

/** Approve & publish each lecture from its review panel. */
export async function approveAndPublishEachLecture(user: ReturnType<typeof userEvent.setup>) {
  const review = await screen.findByRole("region", { name: /lecture canvases/i });
  const lectureNames = within(review)
    .getAllByRole("button", { name: /review lecture canvas for/i })
    .map((button) => button.getAttribute("aria-label") ?? "");
  for (const [index, name] of lectureNames.entries()) {
    await user.click(within(review).getByRole("button", { name }));
    await user.click(await screen.findByRole("button", { name: "Approve & publish" }));
    await within(review).findByText(
      new RegExp(`${index + 1} of ${lectureNames.length} approved`, "i"),
    );
  }
}

export async function approveAllPracticeDesigns(user: ReturnType<typeof userEvent.setup>) {
  const navigation = await screen.findByRole("navigation", { name: "Learning plan lectures" });
  const count = within(navigation).getAllByRole("button").length;
  // "Approve all open goals" is the default action once every lecture's goals are ready.
  const approveAll = await screen.findByRole(
    "button",
    { name: `Approve all open goals (${count})` },
    { timeout: 5_000 },
  );
  await user.click(approveAll);
  await waitFor(() => {
    if (navigation.isConnected && within(navigation).queryAllByText(/^Approved$/).length < count)
      throw new Error("Approval pending");
  });
}

export function soccerCanvasSection() {
  return {
    id: "student-soccer-bayes-example",
    title: "Soccer scouting example",
    source_ref: "student workspace",
    blocks: [
      {
        id: "student-soccer-bayes-example-p-1",
        type: "paragraph",
        text: "A scouting report is evidence that updates the posterior belief about a player fit.",
        items: [],
      },
      {
        id: "student-soccer-bayes-example-list",
        type: "list",
        items: ["Prior player fit", "Likelihood of report", "Decision risk of signing"],
      },
    ],
  };
}
