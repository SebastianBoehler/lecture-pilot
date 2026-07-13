import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChangelogPage } from "./ChangelogPage";
import { renderWithI18n } from "./test/renderWithI18n";

describe("ChangelogPage", () => {
  it("shows product-level releases and links each version to GitHub", () => {
    renderWithI18n(<ChangelogPage onBack={() => undefined} />);

    expect(screen.getByRole("heading", { name: "What's new in LecturePilot" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /v0\.2\.0 on GitHub/i })).toHaveAttribute(
      "href",
      "https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.2.0",
    );
    expect(screen.getByText("From feedback")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /first LecturePilot foundation/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/feat\(|fix\(|chore\(/i)).not.toBeInTheDocument();
  });

  it("renders the release history in German and returns to the previous view", async () => {
    const onBack = vi.fn();
    const user = userEvent.setup();
    renderWithI18n(<ChangelogPage onBack={onBack} />, { locale: "de" });

    expect(screen.getByRole("heading", { name: "Neu in LecturePilot" })).toBeInTheDocument();
    expect(screen.getByText("Aus Feedback")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Zurück" }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});
