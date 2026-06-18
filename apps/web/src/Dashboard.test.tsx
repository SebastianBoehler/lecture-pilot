import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

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
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

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

  it("runs the exam readiness check from published course lectures", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async () => json(examReadinessPayload()));
    vi.stubGlobal("fetch", fetchMock);
    const onOpen = renderDashboard(matchedSession, true);

    await user.click(screen.getByRole("button", { name: /start check/i }));

    expect(await screen.findByText(/which quantity should be minimized/i)).toBeInTheDocument();
    await user.click(screen.getByLabelText(/posterior probability alone/i));
    await user.type(screen.getByPlaceholderText(/write a concise exam-style answer/i), "Use Bayes and compare risks.");
    await user.click(screen.getByRole("button", { name: /check readiness/i }));

    expect(await screen.findByText(/keep reviewing/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /review lecture 03/i }));
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: "lecture-03" }));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/courses/martius-ml/exam-readiness"),
      expect.objectContaining({ headers: expect.any(Object) }),
    );
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
  const onOpen = vi.fn();
  render(
    <Dashboard
      lectures={lectures}
      publishedLectureIds={tutorWorkspacePublished ? ["lecture-03"] : []}
      session={session}
      workspaceCourse={workspaceCourse}
      onOpen={onOpen}
      onSetAttendance={vi.fn()}
    />,
  );
  return onOpen;
}

function workspaceArticle(title: string) {
  const article = screen.getByRole("heading", { name: title }).closest("article");
  expect(article).not.toBeNull();
  return article as HTMLElement;
}

function examReadinessPayload() {
  return {
    course_id: "martius-ml",
    passing_score: 0.7,
    published_lecture_count: 1,
    coverage: [{ lecture_id: "lecture-03", lecture_title: "Bayesian Decision Theory", question_count: 2 }],
    questions: [
      {
        id: "lecture-03:losses-and-risks-quiz",
        kind: "multiple_choice",
        lecture_id: "lecture-03",
        lecture_title: "Bayesian Decision Theory",
        section_id: "losses-and-risks",
        section_title: "Losses and risks",
        prompt: "Which quantity should be minimized when mistakes have different costs?",
        options: ["Posterior probability alone", "Expected risk", "Raw evidence count"],
        answer_index: 1,
        rubric: ["Expected risk combines posterior probabilities with loss values."],
      },
      {
        id: "lecture-03:bayes-formula:open",
        kind: "open_ended",
        lecture_id: "lecture-03",
        lecture_title: "Bayesian Decision Theory",
        section_id: "bayes-formula",
        section_title: "Bayes formula",
        prompt: "Explain Bayes formula as you would in an exam answer.",
        options: [],
        answer_index: null,
        rubric: ["Bayes formula turns evidence into a posterior distribution."],
      },
    ],
  };
}

function json(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}
