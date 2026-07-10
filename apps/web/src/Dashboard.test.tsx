import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { lectures } from "./sampleData";
import { renderWithI18n } from "./test/renderWithI18n";
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

  it("keeps real enrolled courses separate and exposes the local development workspace", () => {
    renderDashboard(realSession, true);

    const nlpCourse = workspaceArticle("INFO4193 Natural Language Processing");
    const workspaceArticleElement = workspaceArticle("Grundlagen des Maschinellen Lernens");

    expect(within(nlpCourse).getByText("No tutor workspace yet")).toBeInTheDocument();
    expect(
      within(nlpCourse).queryByRole("button", { name: /open lecture/i }),
    ).not.toBeInTheDocument();
    expect(within(workspaceArticleElement).getByText("AI tutor available")).toBeInTheDocument();
    expect(
      within(workspaceArticleElement).getByRole("button", { name: /open lecture 03/i }),
    ).toBeInTheDocument();
  });

  it("honors the local demo bridge for non-enrolled accounts", () => {
    window.localStorage.setItem(
      "lecturepilot.demo.workspaceCourse",
      JSON.stringify(workspaceCourse),
    );
    renderDashboard(realSession, true);

    const workspaceArticleElement = workspaceArticle("Grundlagen des Maschinellen Lernens");

    expect(within(workspaceArticleElement).getByText("AI tutor available")).toBeInTheDocument();
    expect(
      within(workspaceArticleElement).queryByText(/not part of your current alma enrollment/i),
    ).not.toBeInTheDocument();
    expect(
      within(workspaceArticleElement).getByRole("button", { name: /open lecture 03/i }),
    ).toBeInTheDocument();
  });

  it("does not duplicate the workspace course when the student is enrolled in the matched course", () => {
    renderDashboard(matchedSession, true);

    expect(
      screen.getAllByRole("heading", { name: "Grundlagen des Maschinellen Lernens" }),
    ).toHaveLength(1);
    expect(screen.getByText("AI tutor available")).toBeInTheDocument();
    expect(screen.queryByText(/not part of your current alma enrollment/i)).not.toBeInTheDocument();
  });

  it("keeps long course lecture lists compact until expanded", async () => {
    const user = userEvent.setup();
    renderDashboard(
      matchedSession,
      true,
      lectures.map((lecture) => lecture.id),
    );

    const workspaceArticleElement = workspaceArticle("Grundlagen des Maschinellen Lernens");
    expect(
      within(workspaceArticleElement).getByRole("button", { name: /open lecture 01/i }),
    ).toBeInTheDocument();
    expect(
      within(workspaceArticleElement).getByRole("button", { name: /open lecture 02/i }),
    ).toBeInTheDocument();
    expect(
      within(workspaceArticleElement).queryByRole("button", { name: /open lecture 03/i }),
    ).not.toBeInTheDocument();

    await user.click(within(workspaceArticleElement).getByRole("button", { name: /show all/i }));

    expect(
      within(workspaceArticleElement).getByRole("button", { name: /open lecture 03/i }),
    ).toBeInTheDocument();
    expect(
      within(workspaceArticleElement).getByRole("button", { name: /show first 2 lectures/i }),
    ).toBeInTheDocument();
  });

  it("hides the discoverable workspace until it is published", () => {
    window.localStorage.setItem(
      "lecturepilot.demo.workspaceCourse",
      JSON.stringify(workspaceCourse),
    );
    renderDashboard(realSession, false);

    expect(
      screen.queryByRole("heading", { name: "Grundlagen des Maschinellen Lernens" }),
    ).not.toBeInTheDocument();
  });

  it("runs the exam readiness check from published course lectures", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/exam-readiness/attempts") && init?.method === "POST") {
        return json(examReadinessAttemptPayload());
      }
      return json(examReadinessPayload());
    });
    vi.stubGlobal("fetch", fetchMock);
    const onOpen = renderDashboard(matchedSession, true);

    expect(screen.queryByRole("dialog", { name: /prüfungs-ready check/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /start exam check/i }));

    const dialog = await screen.findByRole("dialog", { name: /prüfungs-ready check/i });
    const quizPrompt = await within(dialog).findByText(/which quantity should be minimized/i);
    expect(quizPrompt).toBeVisible();
    expect(
      screen.queryByText(/expected risk combines posterior probabilities/i),
    ).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /close exam readiness check/i }));
    expect(screen.queryByRole("dialog", { name: /prüfungs-ready check/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open check/i }));

    const reopenedDialog = await screen.findByRole("dialog", { name: /prüfungs-ready check/i });
    expect(within(reopenedDialog).getByText(/which quantity should be minimized/i)).toBeVisible();
    await user.click(within(reopenedDialog).getByLabelText(/posterior probability alone/i));
    await user.type(
      within(reopenedDialog).getByPlaceholderText(/write a concise exam-style answer/i),
      "Use Bayes and compare risks.",
    );
    await user.click(within(reopenedDialog).getByRole("button", { name: /check readiness/i }));

    expect(await within(reopenedDialog).findByText(/keep reviewing/i)).toBeInTheDocument();
    expect(screen.getAllByText(/expected risk combines posterior probabilities/i)).toHaveLength(1);
    expect(within(reopenedDialog).getByText(/rubric review needed/i)).toBeInTheDocument();
    await user.click(within(reopenedDialog).getByRole("button", { name: /review lecture 03/i }));
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: "lecture-03" }));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/courses/martius-ml/exam-readiness"),
      expect.objectContaining({ headers: expect.any(Object) }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/courses/martius-ml/exam-readiness/attempts"),
      expect.objectContaining({
        body: expect.stringContaining("Bayes and compare risks"),
        method: "POST",
      }),
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

function renderDashboard(
  session: LoginSession,
  tutorWorkspacePublished: boolean,
  publishedLectureIds = tutorWorkspacePublished ? ["lecture-03"] : [],
) {
  const onOpen = vi.fn();
  renderWithI18n(
    <Dashboard
      lectures={lectures}
      publishedLectureIds={publishedLectureIds}
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
    coverage: [
      { lecture_id: "lecture-03", lecture_title: "Bayesian Decision Theory", question_count: 2 },
    ],
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
      },
    ],
  };
}

function examReadinessAttemptPayload() {
  return {
    attempt_id: "attempt-20260701T120000Z0000",
    created_at: "2026-07-01T12:00:00+00:00",
    course_id: "martius-ml",
    passing_score: 0.7,
    score: 0,
    guidance_level: "scaffolded",
    results: [
      {
        question_id: "lecture-03:losses-and-risks-quiz",
        kind: "multiple_choice",
        lecture_id: "lecture-03",
        section_id: "losses-and-risks",
        answer_kind: "multiple_choice",
        correct: false,
        selected_index: 0,
        correct_index: 1,
        status: "incorrect",
      },
      {
        question_id: "lecture-03:bayes-formula:open",
        kind: "open_ended",
        lecture_id: "lecture-03",
        section_id: "bayes-formula",
        answer_kind: "open_ended",
        correct: null,
        status: "needs_rubric_review",
      },
    ],
    tasks: [
      {
        id: "lecture-03-losses-and-risks-quiz-review",
        question_id: "lecture-03:losses-and-risks-quiz",
        kind: "review_wrong_mc",
        status: "open",
        guidance_level: "scaffolded",
        lecture_id: "lecture-03",
        lecture_title: "Bayesian Decision Theory",
        section_id: "losses-and-risks",
        section_title: "Losses and risks",
        prompt: "Which quantity should be minimized when mistakes have different costs?",
        source_ref: "Lecture03-eng.tex frames 8-9",
        rubric: ["Expected risk combines posterior probabilities with loss values."],
        expected_evidence: "Expected risk combines posterior probabilities with loss values.",
        next_action: "Review Losses and risks, then answer a follow-up without seeing the options.",
      },
      {
        id: "lecture-03-bayes-formula-open-review",
        question_id: "lecture-03:bayes-formula:open",
        kind: "review_open_answer",
        status: "open",
        guidance_level: "scaffolded",
        lecture_id: "lecture-03",
        lecture_title: "Bayesian Decision Theory",
        section_id: "bayes-formula",
        section_title: "Bayes formula",
        prompt: "Explain Bayes formula as you would in an exam answer.",
        source_ref: "Lecture03-eng.tex frames 5-6",
        rubric: ["Bayes formula turns evidence into a posterior distribution."],
        expected_evidence: "Bayes formula turns evidence into a posterior distribution.",
        next_action:
          "Compare your answer with the rubric for Bayes formula and revise the weak point.",
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
