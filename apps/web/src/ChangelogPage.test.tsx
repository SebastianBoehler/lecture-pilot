import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChangelogPage } from "./ChangelogPage";
import { renderWithI18n } from "./test/renderWithI18n";

describe("ChangelogPage", () => {
  it("reduces each release to one title, a date, summary, and brief bullets", () => {
    renderWithI18n(<ChangelogPage />);

    expect(screen.getByRole("heading", { name: "What's new in LecturePilot" })).toBeInTheDocument();
    const releases = screen.getAllByRole("article");
    const latestRelease = within(releases[0]);
    expect(latestRelease.getAllByRole("heading")).toHaveLength(1);
    expect(
      latestRelease.getByRole("heading", {
        level: 2,
        name: "Guided onboarding and reliable teaching workflows",
      }),
    ).toBeInTheDocument();
    expect(latestRelease.getByText("7 September 2026")).toBeInTheDocument();
    expect(latestRelease.getByRole("link", { name: /v0\.7\.0 on GitHub/i })).toHaveAttribute(
      "href",
      "https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.7.0",
    );
    expect(latestRelease.getByText("A guided video introduction")).toBeInTheDocument();
    expect(latestRelease.getByText("Private annotations and focused learning")).toBeInTheDocument();
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

  it("renders the release history in German", () => {
    renderWithI18n(<ChangelogPage />, { locale: "de" });

    expect(screen.getByRole("heading", { name: "Neu in LecturePilot" })).toBeInTheDocument();
    const latestRelease = within(screen.getAllByRole("article")[0]);
    expect(latestRelease.getByText("7. September 2026")).toBeInTheDocument();
    expect(latestRelease.getByText("Geführte Videoeinführung")).toBeInTheDocument();
    expect(
      latestRelease.getByText("Private Kommentare und fokussiertes Lernen"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Aus Feedback")).not.toBeInTheDocument();
  });
});
