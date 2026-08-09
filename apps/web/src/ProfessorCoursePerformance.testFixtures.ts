export function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

export function course() {
  return {
    id: "demo-ml-course",
    professor: "professor-demo",
    term: "Summer 2026",
    title: "Demo ML Course",
  };
}

export function lecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-09",
    id: "lecture-01",
    number: "01",
    title: "Introduction",
  };
}

export function secondLecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-16",
    id: "lecture-02",
    number: "02",
    title: "Second lecture",
  };
}

export function noActivityAnalytics() {
  return {
    course_id: "demo-ml-course",
    current_learning_map_revision: "map-1",
    current_publication_version: 1,
    gates: [],
    lecture_id: "lecture-01",
    quizzes: [],
    activity_events: 0,
    unique_learners: 0,
  };
}

export function noActivityCourse() {
  return {
    activity_events: 0,
    correction_after_feedback: cell("correction_after_feedback", 0, null),
    course_id: "demo-ml-course",
    delayed_transfer: cell("delayed_transfer", 0, null),
    independent_first_pass: cell("independent_first_pass", 0, null),
    lectures: [
      {
        activity_events: 0,
        correction_after_feedback: cell("correction_after_feedback", 0, null),
        current_publication_version: 1,
        delayed_transfer: cell("delayed_transfer", 0, null),
        independent_first_pass: cell("independent_first_pass", 0, null),
        lecture_id: "lecture-01",
        quiz_first_attempt: cell("quiz_first_attempt", 0, null),
        supported_retry: cell("supported_retry", 0, null),
        unique_learners: 0,
      },
    ],
    quiz_first_attempt: cell("quiz_first_attempt", 0, null),
    supported_retry: cell("supported_retry", 0, null),
    unique_learners: 0,
  };
}

export function activityAnalytics(lectureId: string) {
  const rate = lectureId === "lecture-02" ? 0.8 : 0.6;
  return {
    course_id: "demo-ml-course",
    current_learning_map_revision: "map-1",
    current_publication_version: 1,
    gates: [],
    lecture_id: lectureId,
    quizzes: [
      {
        activity_events: 5,
        component_id: "quiz-1",
        component_type: "quiz",
        correction_after_feedback: cell("correction_after_feedback", 2, null),
        first_attempt: cell("quiz_first_attempt", 5, rate),
        options: [],
        publication_version: 1,
        question: "Question",
        title: "Quiz",
        unique_learners: 5,
        version_status: "current",
      },
    ],
    activity_events: 5,
    unique_learners: 5,
  };
}

export function courseActivityAnalytics() {
  return {
    activity_events: 10,
    correction_after_feedback: cell("correction_after_feedback", 3, null),
    course_id: "demo-ml-course",
    delayed_transfer: cell("delayed_transfer", 0, null),
    independent_first_pass: cell("independent_first_pass", 0, null),
    lectures: [
      {
        activity_events: 5,
        correction_after_feedback: cell("correction_after_feedback", 2, null),
        current_publication_version: 1,
        delayed_transfer: cell("delayed_transfer", 0, null),
        independent_first_pass: cell("independent_first_pass", 0, null),
        lecture_id: "lecture-01",
        quiz_first_attempt: cell("quiz_first_attempt", 5, 0.6),
        supported_retry: cell("supported_retry", 0, null),
        unique_learners: 5,
      },
      {
        activity_events: 5,
        correction_after_feedback: cell("correction_after_feedback", 1, null),
        current_publication_version: 1,
        delayed_transfer: cell("delayed_transfer", 0, null),
        independent_first_pass: cell("independent_first_pass", 0, null),
        lecture_id: "lecture-02",
        quiz_first_attempt: cell("quiz_first_attempt", 5, 0.8),
        supported_retry: cell("supported_retry", 0, null),
        unique_learners: 5,
      },
    ],
    quiz_first_attempt: cell("quiz_first_attempt", 5, 0.7),
    supported_retry: cell("supported_retry", 0, null),
    unique_learners: 5,
  };
}

function cell(evidenceType: string, sampleSize: number, rate: number | null) {
  return {
    data_status: rate === null ? "insufficient_data" : "available",
    evidence_type: evidenceType,
    rate,
    sample_size: sampleSize,
  };
}

export function session() {
  return {
    courses: [course()],
    roles: ["professor" as const],
    term: "Summer 2026",
    username: "professor-demo",
  };
}
