import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { lectures } from "./sampleData";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession } from "./types";

const realSession: LoginSession = {
  username: "zxoic73",
  display_name: "Sebastian Böhler",
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
  university_courses: [
    {
      source: "alma",
      external_course_id: "unit:42",
      title: "Grundlagen des Maschinellen Lernens",
      organization: "Fachbereich Informatik",
      term: "Sommer 2026",
    },
  ],
};

const observationSession: LoginSession = {
  ...realSession,
  courses: [],
  university_courses: [
    {
      source: "alma",
      external_course_id: "unit:101",
      title: "INFO4193 Natural Language Processing",
      organization: "Fachbereich Informatik",
      term: "Sommer 2026",
    },
    {
      source: "ilias",
      external_course_id: "crs:202",
      title: "INFO4193 Natural Language Processing",
      term: "Sommer 2026",
    },
    {
      source: "alma",
      external_course_id: "unit:303",
      title: "Introduction to Data Ethics",
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

    expect(within(nlpCourse).getByText("Not supported yet")).toBeInTheDocument();
    expect(
      within(nlpCourse).queryByRole("button", { name: /open lecture/i }),
    ).not.toBeInTheDocument();
    expect(within(workspaceArticleElement).getByText("AI tutor available")).toBeInTheDocument();
    expect(
      within(workspaceArticleElement).getByRole("button", { name: /open lecture 03/i }),
    ).toBeInTheDocument();
  });

  it("greets the learner by profile name instead of email or username", () => {
    renderDashboard(realSession, false);

    expect(screen.getByRole("heading", { name: "Welcome, Sebastian Böhler" })).toBeInTheDocument();
    expect(screen.queryByText(/zxoic73@uni-tuebingen.de/)).not.toBeInTheDocument();
  });

  it("shows course skeletons while university data synchronizes", () => {
    renderDashboard(
      {
        ...realSession,
        courses: [],
        university_courses: [],
        university_course_sync_status: "loading",
      },
      false,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Loading your university courses");
    expect(
      screen.queryByRole("heading", { name: /natural language processing/i }),
    ).not.toBeInTheDocument();
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

  it("shows unmatched university enrollments once as minimal unsupported rows", () => {
    renderDashboard(observationSession, false);

    expect(
      screen.getAllByRole("heading", { name: "INFO4193 Natural Language Processing" }),
    ).toHaveLength(1);
    const nlpCourse = workspaceArticle("INFO4193 Natural Language Processing");
    expect(within(nlpCourse).getByText("Not supported yet")).toBeInTheDocument();
    expect(within(nlpCourse).getByText("Alma")).toBeInTheDocument();
    expect(within(nlpCourse).getByText("ILIAS")).toBeInTheDocument();
    expect(within(nlpCourse).queryByText("Fachbereich Informatik")).not.toBeInTheDocument();
    expect(within(nlpCourse).queryByRole("button")).not.toBeInTheDocument();
    expect(within(nlpCourse).queryByText(/no matched lecturepilot/i)).not.toBeInTheDocument();

    const dataEthicsCourse = workspaceArticle("Introduction to Data Ethics");
    expect(within(dataEthicsCourse).getByText("Alma")).toBeInTheDocument();
    expect(within(dataEthicsCourse).queryByText("ILIAS")).not.toBeInTheDocument();
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

    expect(screen.queryByRole("dialog", { name: /exam readiness check/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /start exam check/i }));

    const dialog = await screen.findByRole("dialog", { name: /exam readiness check/i });
    const quizPrompt = await within(dialog).findByText(/which quantity should be minimized/i);
    expect(quizPrompt).toBeVisible();
    expect(quizPrompt).toHaveFocus();
    expect(within(dialog).getByText(/question 1 of 2/i)).toBeVisible();
    expect(within(dialog).getByRole("button", { name: /next question/i })).toBeDisabled();
    expect(
      within(dialog).queryByText(/explain bayes formula as you would in an exam answer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/expected risk combines posterior probabilities/i),
    ).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /close exam readiness check/i }));
    expect(screen.queryByRole("dialog", { name: /exam readiness check/i })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /open check/i })).toHaveFocus());
    await user.click(screen.getByRole("button", { name: /open check/i }));

    const reopenedDialog = await screen.findByRole("dialog", { name: /exam readiness check/i });
    expect(within(reopenedDialog).getByText(/which quantity should be minimized/i)).toBeVisible();
    await user.click(within(reopenedDialog).getByLabelText(/posterior probability alone/i));
    await user.click(within(reopenedDialog).getByRole("button", { name: /next question/i }));
    expect(within(reopenedDialog).getByText(/question 2 of 2/i)).toBeVisible();
    expect(
      within(reopenedDialog).getByText(/explain bayes formula as you would in an exam answer/i),
    ).toHaveFocus();
    expect(
      within(reopenedDialog).queryByText(/which quantity should be minimized/i),
    ).not.toBeInTheDocument();
    await user.type(
      within(reopenedDialog).getByPlaceholderText(/write a concise exam-style answer/i),
      "Use Bayes and compare risks.",
    );
    await user.click(within(reopenedDialog).getByRole("button", { name: /check readiness/i }));

    expect(await within(reopenedDialog).findByText(/keep reviewing/i)).toHaveFocus();
    expect(within(reopenedDialog).getByText("38%")).toBeInTheDocument();
    expect(
      await within(reopenedDialog).findByText("Good explanation; add one concrete failure mode."),
    ).toBeInTheDocument();
    expect(within(reopenedDialog).getByText("Bayes formula")).toBeInTheDocument();
    expect(within(reopenedDialog).queryByText(/awaiting rubric review/i)).not.toBeInTheDocument();
    const resultSummary = within(reopenedDialog).getByRole("list", { name: /result summary/i });
    expect(resultSummary).toHaveTextContent(/1 priority/i);
    expect(
      within(reopenedDialog).getByText(/expected risk combines posterior probabilities/i),
    ).not.toBeVisible();
    await user.click(within(reopenedDialog).getAllByText(/source detail/i)[0]);
    expect(
      within(reopenedDialog).getByText(/expected risk combines posterior probabilities/i),
    ).toBeInTheDocument();
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
    score: 0.375,
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
        status: "evaluated",
        score: 0.75,
        feedback: "Good explanation; add one concrete failure mode.",
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
    ],
  };
}

function json(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}
