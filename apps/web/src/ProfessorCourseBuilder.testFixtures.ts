import { vi } from "vitest";

export function professorFetchMock() {
  const publishedLectures = new Set<string>();
  const deletedCourses = new Set<string>();
  const selectedMedia = new Map<string, { video: ReturnType<typeof youtubeCandidate> }>();
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url, "http://localhost").pathname;
    if (path === "/admin/courses") {
      return json(deletedCourses.has("demo-ml-course") ? [] : [courseWorkspacePayload()]);
    }
    if (path === "/courses")
      return json(deletedCourses.has("demo-ml-course") ? [] : [workspaceCourse()]);
    if (path.match(/^\/courses\/[^/]+\/lectures$/)) return json(lectureListPayload());
    if (path.match(/^\/admin\/courses\/[^/]+$/) && init?.method === "DELETE") {
      const courseId = path.match(/admin\/courses\/([^/]+)$/)?.[1] ?? "demo-ml-course";
      deletedCourses.add(courseId);
      return json({
        course_id: courseId,
        deleted: true,
        deleted_path: `.lecturepilot/courses/${courseId}`,
      });
    }
    if (url.endsWith("/admin/course-workspaces")) return json(courseWorkspacePayload(init));
    if (url.includes("/lecture-schedule")) return json(lectureSchedulePayload());
    if (url.includes("/source-bundle")) return json(sourceBundle());
    if (url.includes("/materials"))
      return json({ path: "uploads/supplement.md", kind: "markdown", size_bytes: 12 });
    if (url.includes("/analytics")) return json(analyticsPayload());
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

function lectureListPayload() {
  const workspace = courseWorkspacePayload({
    body: JSON.stringify({
      lectures: lectureSchedulePayload().lectures,
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

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

function sourceBundle() {
  return {
    course_id: "demo-ml-course",
    files: [
      { path: "Lecture03-eng.tex", kind: "latex", size_bytes: 1000 },
      { path: "Ch3/Venn_C-X_1.pdf", kind: "pdf", size_bytes: 2000 },
      { path: "videos/demo.mp4", kind: "video", size_bytes: 3000 },
    ],
    counts_by_kind: { latex: 1, pdf: 1, video: 1 },
  };
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

function analyticsPayload() {
  return {
    course_id: "demo-ml-course",
    lecture_id: "lecture-03",
    total_events: 3,
    quizzes: [
      {
        component_id: "risk-check",
        component_type: "single_choice_quiz",
        title: "Risk threshold check",
        question: "Which action minimizes expected risk?",
        total_attempts: 2,
        unique_learners: 2,
        correct_attempts: 1,
        correct_rate: 0.5,
        attendance_split: { absent: 1, present: 1 },
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
        total_events: 1,
        unique_learners: 1,
        status_counts: { passed: 1 },
        attendance_split: { present: 1 },
        independent_attempts: 1,
        independent_passes: 1,
        supported_attempts: 0,
        transfer_attempts: 0,
        independent_transfer_passes: 0,
        assistance_level_counts: { none: 1 },
        evidence_counts: { "posterior-and-risk": 1 },
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
          evidence_required: "Connect posterior and loss.",
          section_id: "aim",
          source_ref: "Lecture03-eng.tex#aim",
        },
      ],
    },
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
