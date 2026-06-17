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
  it("keeps real enrolled courses separate from a non-enrolled workspace by default", () => {
    renderDashboard(realSession, true);

    const nlpCourse = workspaceArticle("INFO4193 Natural Language Processing");

    expect(within(nlpCourse).getByText("No tutor workspace yet")).toBeInTheDocument();
    expect(within(nlpCourse).queryByRole("button", { name: /open lecture/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Grundlagen des Maschinellen Lernens" })).not.toBeInTheDocument();
  });

  it("shows the created workspace to a non-enrolled account only with the local demo bridge", () => {
    window.localStorage.setItem("lecturepilot.demo.workspaceCourse", JSON.stringify(workspaceCourse));
    renderDashboard(realSession, true);

    const workspaceArticleElement = workspaceArticle("Grundlagen des Maschinellen Lernens");

    expect(within(workspaceArticleElement).getByText("AI tutor available")).toBeInTheDocument();
    expect(within(workspaceArticleElement).queryByText(/not part of your current alma enrollment/i)).not.toBeInTheDocument();
    expect(within(workspaceArticleElement).getByRole("button", { name: /open lecture 03/i })).toBeInTheDocument();
  });

  it("does not duplicate the workspace course when the student is enrolled in the matched course", () => {
    renderDashboard(matchedSession, true);

    expect(screen.getAllByRole("heading", { name: "Grundlagen des Maschinellen Lernens" })).toHaveLength(1);
    expect(screen.getByText("AI tutor available")).toBeInTheDocument();
    expect(screen.queryByText(/not part of your current alma enrollment/i)).not.toBeInTheDocument();
  });

  it("hides the discoverable workspace until it is published", () => {
    window.localStorage.setItem("lecturepilot.demo.workspaceCourse", JSON.stringify(workspaceCourse));
    renderDashboard(realSession, false);

    expect(screen.queryByRole("heading", { name: "Grundlagen des Maschinellen Lernens" })).not.toBeInTheDocument();
  });
});

const workspaceCourse = {
  access_policy: "tuebingen_enrolled" as const,
  id: "martius-ml",
  title: "Grundlagen des Maschinellen Lernens",
  professor: "Prof. Georg Martius",
  term: "Sommer 2026",
};

function renderDashboard(session: LoginSession, tutorWorkspacePublished: boolean) {
  render(
    <Dashboard
      lectures={lectures}
      publishedLectureIds={tutorWorkspacePublished ? ["lecture-03"] : []}
      session={session}
      workspaceCourse={workspaceCourse}
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
