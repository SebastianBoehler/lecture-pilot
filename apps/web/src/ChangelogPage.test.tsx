import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChangelogPage } from "./ChangelogPage";
import { renderWithI18n } from "./test/renderWithI18n";

describe("ChangelogPage", () => {
  it("reduces each release to one title, a date, summary, and brief bullets", () => {
    renderWithI18n(<ChangelogPage onBack={() => undefined} />);

    expect(screen.getByRole("heading", { name: "What's new in LecturePilot" })).toBeInTheDocument();
    const releases = screen.getAllByRole("article");
    const latestRelease = within(releases[0]);
    expect(latestRelease.getAllByRole("heading")).toHaveLength(1);
    expect(
      latestRelease.getByRole("heading", {
        level: 2,
        name: "A complete pilot flow for students and lecturers",
      }),
    ).toBeInTheDocument();
    expect(latestRelease.getByText("13 July 2026")).toBeInTheDocument();
    expect(latestRelease.getByRole("link", { name: /v0\.2\.0 on GitHub/i })).toHaveAttribute(
      "href",
      "https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.2.0",
    );
    expect(latestRelease.getByText("University accounts and courses")).toBeInTheDocument();
    expect(
      latestRelease.queryByText(/students and lecturers sign in through Alma/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Latest")).not.toBeInTheDocument();
    expect(screen.queryByText("From feedback")).not.toBeInTheDocument();
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
    expect(screen.getByText("13. Juli 2026")).toBeInTheDocument();
    expect(screen.getByText("Uni-Konten und Kurse")).toBeInTheDocument();
    expect(screen.queryByText("Aus Feedback")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Zurück" }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});
