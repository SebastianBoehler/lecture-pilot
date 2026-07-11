import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

export async function showAllPublishedLectures(user: ReturnType<typeof userEvent.setup>) {
  if (screen.queryByRole("button", { name: /open lecture 03/i })) return;
  const showAll = screen.queryByRole("button", { name: /show all/i });
  const toggle = showAll ?? (await screen.findByRole("button", { name: /show all/i }));
  await user.click(toggle);
}

export async function openLecture03FromDashboard(user: ReturnType<typeof userEvent.setup>) {
  await showAllPublishedLectures(user);
  await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
  await screen.findByLabelText(/open tutor chat/i);
}

export async function openProfessorDemo(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /preview professor account/i }));
  await screen.findByRole("navigation", { name: /course builder progress/i });
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
