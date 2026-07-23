import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FeedbackDialog } from "./FeedbackDialog";
import { renderWithI18n } from "./test/renderWithI18n";

describe("FeedbackDialog", () => {
  it("offers feedback, feature request, and bug report categories", async () => {
    const user = userEvent.setup();
    renderWithI18n(
      <FeedbackDialog
        accountType="student"
        context={{ courseTitle: "Machine Learning", lectureTitle: "Introduction" }}
        open
        source="manual"
        onClose={vi.fn()}
      />,
    );
    const dialog = screen.getByRole("dialog", { name: /send feedback/i });

    expect(within(dialog).getByRole("option", { name: "Feedback" })).toBeInTheDocument();
    expect(within(dialog).getByRole("option", { name: "Feature request" })).toBeInTheDocument();
    expect(within(dialog).getByRole("option", { name: "Report a bug" })).toBeInTheDocument();

    await user.selectOptions(within(dialog).getByLabelText(/category/i), "feature");
    await user.type(within(dialog).getByLabelText(/message/i), "Please add keyboard shortcuts.");
    const email = within(dialog).getByRole("link", { name: /open email draft/i });
    expect(decodeURIComponent(email.getAttribute("href") ?? "")).toContain(
      "Please add keyboard shortcuts.",
    );
    expect(decodeURIComponent(email.getAttribute("href") ?? "")).toContain(
      "subject=LecturePilot feature request",
    );
  });
});
