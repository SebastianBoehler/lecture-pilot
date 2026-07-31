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
    gates: [],
    lecture_id: "lecture-01",
    quizzes: [],
    total_events: 0,
  };
}

export function noActivityCourse() {
  return {
    course_id: "demo-ml-course",
    gate_checks: 0,
    gate_passes: 0,
    gate_rate: null,
    lectures: [
      {
        gate_checks: 0,
        gate_passes: 0,
        gate_rate: null,
        lecture_id: "lecture-01",
        quiz_attempts: 0,
        quiz_correct_attempts: 0,
        quiz_rate: null,
        total_events: 0,
        unique_learners: 0,
      },
    ],
    quiz_attempts: 0,
    quiz_correct_attempts: 0,
    quiz_rate: null,
    total_events: 0,
    unique_learners: 0,
  };
}

export function activityAnalytics(lectureId: string) {
  return {
    course_id: "demo-ml-course",
    gates: [],
    lecture_id: lectureId,
    quizzes: [
      {
        attendance_split: { present: 2 },
        component_id: "quiz-1",
        component_type: "quiz",
        correct_attempts: 1,
        correct_rate: 0.5,
        options: [],
        question: "Question",
        title: "Quiz",
        total_attempts: 2,
        unique_learners: 2,
      },
    ],
    total_events: 2,
  };
}

export function courseActivityAnalytics() {
  return {
    course_id: "demo-ml-course",
    gate_checks: 0,
    gate_passes: 0,
    gate_rate: null,
    lectures: [
      {
        gate_checks: 0,
        gate_passes: 0,
        gate_rate: null,
        lecture_id: "lecture-01",
        quiz_attempts: 2,
        quiz_correct_attempts: 1,
        quiz_rate: 0.5,
        total_events: 2,
        unique_learners: 2,
      },
      {
        gate_checks: 0,
        gate_passes: 0,
        gate_rate: null,
        lecture_id: "lecture-02",
        quiz_attempts: 1,
        quiz_correct_attempts: 1,
        quiz_rate: 1,
        total_events: 1,
        unique_learners: 1,
      },
    ],
    quiz_attempts: 3,
    quiz_correct_attempts: 2,
    quiz_rate: 0.6667,
    total_events: 3,
    unique_learners: 2,
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
