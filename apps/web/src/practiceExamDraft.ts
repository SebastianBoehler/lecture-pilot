import type { PracticeExamAnswers } from "./practiceExamTypes";

const PREFIX = "lecturepilot.practice-exam-draft.";
const ACCOUNT_KEY = `${PREFIX}account`;

export function readPracticeExamDraft(
  accountId: string,
  courseId: string,
  examId: string,
): PracticeExamAnswers {
  try {
    const value = window.sessionStorage.getItem(key(accountId, courseId, examId));
    return value ? (JSON.parse(value) as PracticeExamAnswers) : {};
  } catch {
    return {};
  }
}

export function savePracticeExamDraft(
  accountId: string,
  courseId: string,
  examId: string,
  answers: PracticeExamAnswers,
) {
  try {
    window.sessionStorage.setItem(key(accountId, courseId, examId), JSON.stringify(answers));
  } catch {
    // A tab can still complete the exam if browser storage is unavailable.
  }
}

export function clearPracticeExamDraft(accountId: string, courseId: string, examId: string) {
  window.sessionStorage.removeItem(key(accountId, courseId, examId));
}

export function ensurePracticeExamDraftAccount(accountId: string) {
  const previous = window.sessionStorage.getItem(ACCOUNT_KEY);
  if (previous && previous !== accountId) clearAllPracticeExamDrafts();
  window.sessionStorage.setItem(ACCOUNT_KEY, accountId);
}

export function clearAllPracticeExamDrafts() {
  for (let index = window.sessionStorage.length - 1; index >= 0; index -= 1) {
    const name = window.sessionStorage.key(index);
    if (name?.startsWith(PREFIX)) window.sessionStorage.removeItem(name);
  }
}

function key(accountId: string, courseId: string, examId: string) {
  return `${PREFIX}${encodeURIComponent(accountId)}.${encodeURIComponent(courseId)}.${examId}`;
}
