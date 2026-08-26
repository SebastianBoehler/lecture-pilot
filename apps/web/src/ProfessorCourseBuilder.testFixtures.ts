import { vi } from "vitest";
import {
  hasConfirmedLectureRoute,
  lectureSourcePath,
  savedWorkspaceScope,
  sourceBundle,
  sourceRouting,
  workspaceScope,
  type FixtureScope,
} from "./ProfessorCourseBuilder.practiceDesignFixture";
import type { PracticeDesign } from "./practiceDesignTypes";
import { learningDesignPayload } from "./testLearningDesignReviewFixture";

export function professorFetchMock({
  staleApprovalOnceFor,
}: { staleApprovalOnceFor?: string } = {}) {
  const publishedLectures = new Set<string>();
  const deletedCourses = new Set<string>();
  const selectedMedia = new Map<string, { video: ReturnType<typeof youtubeCandidate> }>();
  const practiceDesigns = new Map<string, PracticeDesign>();
  let scope: FixtureScope = "single-lecture";
  let routing = sourceRouting(false, scope);
  let workspaceCreated = false;
  let staleApprovalConsumed = false;
  const learningDesignApprovals = new Set<string>();
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url, "http://localhost").pathname;
    function restoreScopeFromSavedFlow() {
      if (workspaceCreated || savedWorkspaceScope() !== "full-course") return;
      scope = "full-course";
      routing = sourceRouting(false, scope);
    }

    if (path === "/admin/courses") {
      return json(deletedCourses.has("demo-ml-course") ? [] : [courseWorkspacePayload()]);
    }
    if (path === "/courses")
      return json(deletedCourses.has("demo-ml-course") ? [] : [workspaceCourse()]);
    if (path.match(/^\/courses\/[^/]+\/lectures$/)) {
      restoreScopeFromSavedFlow();
      return json(lectureListPayload(scope));
    }
    if (path.match(/^\/admin\/courses\/[^/]+$/) && init?.method === "DELETE") {
      const courseId = path.match(/admin\/courses\/([^/]+)$/)?.[1] ?? "demo-ml-course";
      deletedCourses.add(courseId);
      return json({
        course_id: courseId,
        deleted: true,
      });
    }
    if (url.endsWith("/admin/course-workspaces")) {
      scope = workspaceScope(init);
      routing = sourceRouting(false, scope);
      workspaceCreated = true;
      return json(courseWorkspacePayload(init));
    }
    if (url.includes("/lecture-schedule")) return json(lectureSchedulePayload());
    if (url.includes("/source-bundle")) {
      restoreScopeFromSavedFlow();
      return json(sourceBundle(scope));
    }
    if (url.includes("/source-routing")) {
      restoreScopeFromSavedFlow();
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body));
        routing = { ...routing, ...body, confirmed: true };
      }
      return json(routing);
    }
    if (url.includes("/practice-design")) {
      const lectureId = path.match(/lectures\/([^/]+)\/practice-design/)?.[1] ?? "lecture-03";
      const design = practiceDesigns.get(lectureId);
      if (path.endsWith("/proposal")) {
        if (!hasConfirmedLectureRoute(routing, lectureId)) {
          return json({ detail: "Confirm a current source route for this lecture first." }, 409);
        }
        const proposed = practiceDesignPayload(lectureId, routing.source_revision);
        practiceDesigns.set(lectureId, proposed);
        return json(proposed);
      }
      if (path.endsWith("/approve") && design) {
        const approval = JSON.parse(String(init?.body));
        if (
          approval.source_revision !== design.source_revision ||
          approval.practice_design_revision !== design.revision
        ) {
          return json(
            { detail: "The practice design or source revision changed. Reload it." },
            409,
          );
        }
        if (!staleApprovalConsumed && lectureId === staleApprovalOnceFor) {
          staleApprovalConsumed = true;
          practiceDesigns.set(lectureId, { ...design, approval: null, revision: "f".repeat(64) });
          return json(
            { detail: "The practice design or source revision changed. Reload it." },
            409,
          );
        }
        const approved = approvePracticeDesign(design);
        practiceDesigns.set(lectureId, approved);
        return json(approved);
      }
      if (init?.method === "PUT" && design) {
        const update = JSON.parse(String(init.body));
        const saved = { ...design, ...update, approval: null, revision: "e".repeat(64) };
        practiceDesigns.set(lectureId, saved);
        return json(saved);
      }
      return design
        ? json(design)
        : json({ detail: "Practice design has not been proposed." }, 404);
    }
    if (url.includes("/materials"))
      return json({ path: "uploads/supplement.md", kind: "markdown", size_bytes: 12 });
    if (path.match(/^\/admin\/courses\/[^/]+\/analytics$/)) {
      return json(courseAnalyticsPayload());
    }
    if (url.includes("/analytics")) return json(analyticsPayload());
    if (url.includes("/canvas/learning-design")) {
      const { courseId, lectureId } = courseAndLectureFromUrl(url);
      const key = `${courseId}:${lectureId}`;
      if (init?.method === "POST") learningDesignApprovals.add(key);
      return json(learningDesignPayload(courseId, lectureId, learningDesignApprovals.has(key)));
    }
    if (url.includes("/canvas/publication"))
      return json(publicationPayload(url, publishedLectures));
    if (url.includes("/canvas/publish")) return json(publishPayload(url, publishedLectures));
    if (url.includes("/canvas/draft")) return json(canvasPayload());
    if (url.includes("/canvas")) return json(canvasPayload());
    if (url.includes("/media/youtube/search")) return json({ items: [youtubeCandidate()] });
    const mediaMatch = path.match(
      /^\/admin\/courses\/[^/]+\/lectures\/([^/]+)\/media\/youtube(?:\/([^/]+))?$/,
    );
    if (mediaMatch) {
      const [, lectureId, pathVideoId] = mediaMatch;
      if (init?.method === "DELETE") {
        const deleted = selectedMedia.delete(`${lectureId}:${pathVideoId}`) ? 1 : 0;
        return json({ deleted });
      }
      if (init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        selectedMedia.set(`${lectureId}:${body.video.video_id}`, { video: body.video });
        return json({ block_id: `youtube-${body.video.video_id}` });
      }
      return json(
        [...selectedMedia.entries()]
          .filter(([key]) => key.startsWith(`${lectureId}:`))
          .map(([, selection]) => selection),
      );
    }
    throw new Error(`Unexpected fetch: ${url} ${init?.method ?? "GET"}`);
  });
}

function courseAndLectureFromUrl(url: string) {
  return {
    courseId: url.match(/courses\/([^/]+)/)?.[1] ?? "demo-ml-course",
    lectureId: url.match(/lectures\/([^/]+)\/canvas/)?.[1] ?? "lecture-03",
  };
}

function publicationPayload(url: string, publishedLectures: Set<string>) {
  const { courseId, lectureId } = courseAndLectureFromUrl(url);
  const published = publishedLectures.has(`${courseId}:${lectureId}`);
  return {
    course_id: courseId,
    lecture_id: lectureId,
    published,
    version: published ? 1 : null,
    published_at: published ? "2026-06-12T10:00:00Z" : null,
  };
}

function publishPayload(url: string, publishedLectures: Set<string>) {
  const { courseId, lectureId } = courseAndLectureFromUrl(url);
  publishedLectures.add(`${courseId}:${lectureId}`);
  return {
    course_id: courseId,
    lecture_id: lectureId,
    published: true,
    version: 1,
    published_at: "2026-06-12T10:00:00Z",
  };
}

function workspaceCourse() {
  return {
    access_policy: "public",
    id: "demo-ml-course",
    title: "Demo ML Course",
    professor: "professor-demo",
    term: "Sommer 2026",
  };
}

function lectureListPayload(scope: FixtureScope) {
  const workspace = courseWorkspacePayload({
    body: JSON.stringify({
      lectures: scope === "full-course" ? lectureSchedulePayload().lectures : [],
      lecture_number: "03",
      lecture_title: "Bayesian Decision Theory",
    }),
  });
  return workspace.lectures.map(
    (lecture: {
      course_id: string;
      date: string;
      id: string;
      material_path?: string;
      title: string;
    }) => ({
      lecture,
      unlocked: true,
      attendance: "unknown",
    }),
  );
}

function json(payload: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload };
}

function lectureSchedulePayload() {
  return {
    course_id: "demo-ml-course",
    source_paths: ["Lecture01-eng.tex", "Lecture02-eng.tex"],
    lectures: [
      { number: "01", title: "Lecture 01", date: "2026-05-06", material_path: "Lecture01-eng.tex" },
      { number: "02", title: "Lecture 02", date: "2026-05-13", material_path: "Lecture02-eng.tex" },
    ],
  };
}

function canvasPayload() {
  return {
    id: "demo-ml-course-lecture-03",
    course_id: "demo-ml-course",
    lecture_id: "lecture-03",
    title: "Bayesian Decision Theory",
    source_kind: "latex",
    source_ref: "Lecture03-eng.tex",
    workspace_path: ".lecturepilot/workspaces/professor-preview/index.md",
    warnings: ["Planner model finished with reason 'error'. Review this draft before publishing."],
    sections: [
      { id: "aim", title: "Decision making", blocks: [] },
      { id: "bayes-formula", title: "Bayes formula", blocks: [] },
    ],
  };
}

function practiceDesignPayload(lectureId: string, sourceRevision: string): PracticeDesign {
  const revision = "d".repeat(64);
  return {
    schema_version: 1,
    course_id: "demo-ml-course",
    lecture_id: lectureId,
    lecture_title: "Bayesian Decision Theory",
    objective: "Calculate a posterior from evidence.",
    source_revision: sourceRevision,
    revision,
    approval: null,
    targets: [
      {
        id: "posterior",
        title: "Posterior",
        outcome: "Calculate a posterior from evidence.",
        baseline_task: "Calculate the posterior.",
        independent_exit_task: "Calculate a new posterior.",
        delayed_transfer_task: "Diagnose a posterior decision.",
        evidence_criteria: [
          { id: "substitute", description: "Uses stated values.", required: true },
        ],
        misconceptions: [],
        hint_ladder: [],
        review_after_days: 7,
        source_refs: [lectureSourcePath(lectureId)],
      },
    ],
  };
}

function approvePracticeDesign(design: PracticeDesign): PracticeDesign {
  return {
    ...design,
    approval: {
      approved_by: "professor-demo",
      approved_at: "2026-08-26T12:00:00Z",
      source_revision: design.source_revision,
      practice_design_revision: design.revision,
    },
  };
}

function analyticsPayload() {
  return {
    course_id: "demo-ml-course",
    lecture_id: "lecture-03",
    activity_events: 10,
    unique_learners: 5,
    current_publication_version: 1,
    current_learning_map_revision: "map-1",
    correction_after_feedback: analyticsCell("correction_after_feedback", 2, null),
    delayed_transfer: analyticsCell("delayed_transfer", 0, null),
    independent_first_pass: analyticsCell("independent_first_pass", 5, 0.6),
    quiz_first_attempt: analyticsCell("quiz_first_attempt", 5, 0.6),
    supported_retry: analyticsCell("supported_retry", 2, null),
    quizzes: [
      {
        component_id: "risk-check",
        component_type: "single_choice_quiz",
        title: "Risk threshold check",
        question: "Which action minimizes expected risk?",
        activity_events: 5,
        unique_learners: 5,
        publication_version: 1,
        learning_map_revision: "map-1",
        version_status: "current",
        first_attempt: analyticsCell("quiz_first_attempt", 5, 0.6),
        correction_after_feedback: analyticsCell("correction_after_feedback", 2, null),
        options: [
          {
            option_index: 0,
            option_id: "prior-only",
            text: "Use the largest class prior.",
            selections: 1,
            correct: false,
          },
          {
            option_index: 1,
            option_id: "posterior-loss",
            text: "Use posterior-weighted loss.",
            selections: 1,
            correct: true,
          },
        ],
      },
    ],
    gates: [
      {
        gate_id: "risk-gate",
        activity_events: 5,
        unique_learners: 5,
        publication_version: 1,
        gate_revision: "revision-1",
        learning_map_revision: "map-1",
        version_status: "current",
        independent_first_pass: analyticsCell("independent_first_pass", 5, 0.6),
        supported_retry: analyticsCell("supported_retry", 2, null),
        delayed_transfer: analyticsCell("delayed_transfer", 0, null),
      },
    ],
    learning_map: {
      course_id: "demo-ml-course",
      lecture_id: "lecture-03",
      title: "Bayesian Decision Theory",
      nodes: [
        {
          id: "aim",
          title: "Decision making",
          lecture_id: "lecture-03",
          section_id: "aim",
          source_ref: "Lecture03-eng.tex#aim",
          prerequisites: [],
          gate_ids: ["risk-gate"],
          quiz_ids: [],
        },
        {
          id: "bayes-formula",
          title: "Bayes formula",
          lecture_id: "lecture-03",
          section_id: "bayes-formula",
          source_ref: "Lecture03-eng.tex#bayes",
          prerequisites: ["aim"],
          gate_ids: [],
          quiz_ids: ["risk-check"],
        },
      ],
      gates: [
        {
          id: "risk-gate",
          concept_id: "aim",
          title: "Risk evidence gate",
          prompt: "Explain expected risk.",
          section_id: "aim",
          source_ref: "Lecture03-eng.tex#aim",
        },
      ],
    },
  };
}

function courseAnalyticsPayload() {
  return {
    activity_events: 10,
    correction_after_feedback: analyticsCell("correction_after_feedback", 2, null),
    course_id: "demo-ml-course",
    delayed_transfer: analyticsCell("delayed_transfer", 0, null),
    independent_first_pass: analyticsCell("independent_first_pass", 5, 0.6),
    lectures: [
      {
        activity_events: 10,
        correction_after_feedback: analyticsCell("correction_after_feedback", 2, null),
        current_learning_map_revision: "map-1",
        current_publication_version: 1,
        delayed_transfer: analyticsCell("delayed_transfer", 0, null),
        independent_first_pass: analyticsCell("independent_first_pass", 5, 0.6),
        lecture_id: "lecture-03",
        quiz_first_attempt: analyticsCell("quiz_first_attempt", 5, 0.6),
        supported_retry: analyticsCell("supported_retry", 2, null),
        unique_learners: 5,
      },
    ],
    quiz_first_attempt: analyticsCell("quiz_first_attempt", 5, 0.6),
    supported_retry: analyticsCell("supported_retry", 2, null),
    unique_learners: 5,
  };
}

function analyticsCell(evidenceType: string, sampleSize: number, rate: number | null) {
  return {
    data_status: rate === null ? "insufficient_data" : "available",
    evidence_type: evidenceType,
    rate,
    sample_size: sampleSize,
  };
}

function courseWorkspacePayload(init?: RequestInit) {
  const body = JSON.parse(String(init?.body ?? "{}"));
  const title = body.course_title ?? "Demo ML Course";
  const lectures = body.lectures?.length
    ? body.lectures.map(
        (lecture: { date: string; material_path?: string; number: string; title: string }) => ({
          id: `lecture-${lecture.number}`,
          course_id: "demo-ml-course",
          title: lecture.title,
          date: lecture.date,
          material_path: lecture.material_path,
        }),
      )
    : [
        {
          id: "lecture-03",
          course_id: "demo-ml-course",
          title: body.lecture_title ?? "Bayesian Decision Theory",
          date: "2026-06-11",
        },
      ];
  return {
    course: {
      access_policy: body.access_policy ?? "tuebingen_enrolled",
      canvas_language: body.canvas_language ?? "en",
      default_publication_mode: "on_lecture_date",
      id: "demo-ml-course",
      title,
      professor: "professor-demo",
      term: "Sommer 2026",
    },
    lectures,
    active_lecture_id: lectures[0].id,
    access_summary: {
      course_id: "demo-ml-course",
      default_rule: {
        audience: body.access_policy ?? "tuebingen_enrolled",
        publication_mode: "on_lecture_date",
        publication_at: null,
      },
      lectures: lectures.map((lecture: { id: string }) => ({
        lecture_id: lecture.id,
        rule_source: "course_default",
        rule: {
          audience: body.access_policy ?? "tuebingen_enrolled",
          publication_mode: "on_lecture_date",
          publication_at: null,
        },
        effective_publication_at: "2026-06-10T22:00:00Z",
        release_status: "released",
        content_ready: false,
      })),
    },
  };
}

function youtubeCandidate() {
  return {
    video_id: "j4yxsEQqPMI",
    title: "Bayesian Decision Theory",
    channel_title: "ML Tuebingen",
    description: "Bayes rule and risk.",
    url: "https://www.youtube.com/watch?v=j4yxsEQqPMI",
    thumbnail_url: "https://i.ytimg.com/vi/j4yxsEQqPMI/hqdefault.jpg",
    duration: { display: "12:15", seconds: 735 },
    score: 9,
    reason: "Matches lecture terms.",
  };
}
