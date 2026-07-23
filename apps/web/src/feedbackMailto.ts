export const FEEDBACK_EMAIL = "s.boehler@student.uni-tuebingen.de";

export type FeedbackCategory = "feedback" | "feature" | "bug";

export type FeedbackMailtoInput = {
  accountType: "student" | "professor";
  appVersion: string;
  browser: string;
  buildId: string;
  category: FeedbackCategory;
  courseTitle?: string;
  lectureTitle?: string;
  locale: string;
  message: string;
  pageUrl: string;
};

export function buildFeedbackMailto(input: FeedbackMailtoInput) {
  const subject = `LecturePilot ${subjectLabel(input.category)}`;
  const context = [
    `Category: ${categoryLabel(input.category)}`,
    `App version: ${input.appVersion}`,
    `Build: ${input.buildId}`,
    `Browser: ${input.browser}`,
    `Page: ${input.pageUrl}`,
    `Account type: ${input.accountType}`,
    `Interface language: ${input.locale}`,
    input.courseTitle ? `Course: ${input.courseTitle}` : "",
    input.lectureTitle ? `Lecture: ${input.lectureTitle}` : "",
  ].filter(Boolean);
  const body = [
    input.message.trim() || "Please write your message here.",
    "",
    "---",
    "Technical context (editable)",
    ...context,
  ].join("\n");
  return `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

function subjectLabel(category: FeedbackCategory) {
  if (category === "feature") return "feature request";
  if (category === "bug") return "bug report";
  return "feedback";
}

function categoryLabel(category: FeedbackCategory) {
  if (category === "feature") return "Feature request";
  if (category === "bug") return "Bug report";
  return "Feedback";
}
