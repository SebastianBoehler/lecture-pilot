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
        name: "Simpler generation and course sharing",
      }),
    ).toBeInTheDocument();
    expect(latestRelease.getByText("12 October 2026")).toBeInTheDocument();
    expect(latestRelease.getByRole("link", { name: /v0\.9\.0 on GitHub/i })).toHaveAttribute(
      "href",
      "https://github.com/SebastianBoehler/lecture-pilot/releases/tag/v0.9.0",
    );
    expect(latestRelease.getByText("Bounded generation with review notes")).toBeInTheDocument();
    expect(latestRelease.getByText("Share courses with links and QR codes")).toBeInTheDocument();
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
    expect(latestRelease.getByText("12. Oktober 2026")).toBeInTheDocument();
    expect(latestRelease.getByText("Begrenzte Generierung mit Prüfhinweisen")).toBeInTheDocument();
    expect(latestRelease.getByText("Kurse mit Links und QR-Codes teilen")).toBeInTheDocument();
    expect(screen.queryByText("Aus Feedback")).not.toBeInTheDocument();
  });
});
