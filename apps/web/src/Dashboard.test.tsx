import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { lectures } from "./sampleData";
import type { LoginSession } from "./types";

const realSession: LoginSession = {
  username: "zxoic73",
  email: "zxoic73@uni-tuebingen.de",
  term: "Sommer 2026",
  roles: ["student"],
  courses: [
    {
      id: "info4193",
      title: "INFO4193 Natural Language Processing",
      professor: "Fachbereich Informatik",
      term: "Sommer 2026",
    },
    {
      id: "info4222",
      title: "INFO4222 Softwarequalität in Theorie und Industrieller Praxis",
      professor: "Fachbereich Informatik",
      term: "Sommer 2026",
    },
  ],
};

const matchedSession: LoginSession = {
  ...realSession,
  courses: [
    {
      id: "martius-ml",
      title: "Grundlagen des Maschinellen Lernens",
      professor: "Prof. Georg Martius",
      term: "Sommer 2026",
    },
  ],
};

describe("Dashboard course workspace matching", () => {
  it("keeps real enrolled courses separate from the published demo workspace", () => {
    renderDashboard(realSession, true);

    const nlpCourse = workspaceArticle("INFO4193 Natural Language Processing");
    const demoCourse = workspaceArticle("Grundlagen des Maschinellen Lernens");

    expect(within(nlpCourse).getByText("No tutor workspace yet")).toBeInTheDocument();
    expect(within(nlpCourse).queryByRole("button", { name: /open lecture/i })).not.toBeInTheDocument();
    expect(within(demoCourse).getByText("Public workspace")).toBeInTheDocument();
    expect(within(demoCourse).getByText(/not part of your current alma enrollment/i)).toBeInTheDocument();
    expect(within(demoCourse).getByRole("button", { name: /open lecture 03/i })).toBeInTheDocument();
  });

  it("does not duplicate the demo course when the student is enrolled in the matched course", () => {
    renderDashboard(matchedSession, true);

    expect(screen.getAllByRole("heading", { name: "Grundlagen des Maschinellen Lernens" })).toHaveLength(1);
    expect(screen.getByText("AI tutor available")).toBeInTheDocument();
    expect(screen.queryByText(/not part of your current alma enrollment/i)).not.toBeInTheDocument();
  });

  it("shows an unpublished demo workspace without enabling lecture entry", () => {
    renderDashboard(realSession, false);

    const demoCourse = workspaceArticle("Grundlagen des Maschinellen Lernens");
    expect(within(demoCourse).getByText("Public workspace")).toBeInTheDocument();
    expect(within(demoCourse).getByText(/no tutor workspace yet/i)).toBeInTheDocument();
    expect(within(demoCourse).queryByRole("button", { name: /open lecture 03/i })).not.toBeInTheDocument();
  });
});

function renderDashboard(session: LoginSession, tutorWorkspacePublished: boolean) {
  render(
    <Dashboard
      lectures={lectures}
      publishedLectureIds={tutorWorkspacePublished ? ["lecture-03"] : []}
      session={session}
      onOpen={vi.fn()}
      onSetAttendance={vi.fn()}
    />,
  );
}

function workspaceArticle(title: string) {
  const article = screen.getByRole("heading", { name: title }).closest("article");
  expect(article).not.toBeNull();
  return article as HTMLElement;
}
