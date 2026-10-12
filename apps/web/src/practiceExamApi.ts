import { apiUrl } from "./api";
import { readApiError } from "./apiError";
import { authRequestInit } from "./authz";
import {
  isTransientPollResponse,
  pollUntil,
  PollTimeoutError,
  retryAfterMs,
  type PollStep,
} from "./polling";
import type {
  PpiCatalog,
  PpiCredentials,
  PpiExamSource,
  PracticeExam,
  PracticeExamGenerationInput,
  PracticeExamGenerationStatus,
  PracticeExamSolutionSheet,
} from "./practiceExamTypes";
import type { LoginSession } from "./types";

export async function listPracticeExams(courseId: string, session: LoginSession) {
  return requestJson<PracticeExam[]>(`/courses/${courseId}/practice-exams`, session);
}

const EXAM_POLL_FIRST_MS = 3_000;
const EXAM_POLL_MAX_MS = 10_000;
const EXAM_POLL_TIMEOUT_MS = 16 * 60 * 1000;

export async function generatePracticeExam(
  courseId: string,
  input: PracticeExamGenerationInput,
  idempotencyKey: string,
  session: LoginSession,
  signal?: AbortSignal,
) {
  const result = await requestJson<PracticeExam | PracticeExamGenerationStatus>(
    `/courses/${courseId}/practice-exam-generations`,
    session,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
      signal,
    },
  );
  if (!("status" in result)) return result;
  let status = result;
  if (status.status === "running") {
    try {
      status = await pollUntil({
        initialDelayMs: EXAM_POLL_FIRST_MS,
        maxDelayMs: EXAM_POLL_MAX_MS,
        timeoutMs: EXAM_POLL_TIMEOUT_MS,
        signal,
        poll: (pollSignal) => pollGenerationStatus(courseId, idempotencyKey, session, pollSignal),
      });
    } catch (error) {
      if (!(error instanceof PollTimeoutError)) throw error;
    }
  }
  if (status.status === "completed" && status.exam_id) {
    return requestJson<PracticeExam>(
      `/courses/${courseId}/practice-exams/${status.exam_id}`,
      session,
      { signal },
    );
  }
  throw new Error(
    status.status === "running"
      ? "Practice exam generation is still running. Retry to check the same job."
      : "Practice exam generation failed. Please retry.",
  );
}

async function pollGenerationStatus(
  courseId: string,
  idempotencyKey: string,
  session: LoginSession,
  signal: AbortSignal | undefined,
): Promise<PollStep<PracticeExamGenerationStatus>> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/practice-exam-generations/status`),
    authRequestInit(session, { headers: { "Idempotency-Key": idempotencyKey }, signal }),
  );
  if (isTransientPollResponse(response)) {
    return { done: false, retryAfterMs: retryAfterMs(response) };
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Practice exam request failed."));
  const status = payload as PracticeExamGenerationStatus;
  return status.status === "running" ? { done: false } : { done: true, value: status };
}

export async function practiceExamGenerationStatus(
  courseId: string,
  idempotencyKey: string,
  session: LoginSession,
) {
  return requestJson<PracticeExamGenerationStatus>(
    `/courses/${courseId}/practice-exam-generations/status`,
    session,
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
}

export async function deletePracticeExam(courseId: string, examId: string, session: LoginSession) {
  await requestJson(`/courses/${courseId}/practice-exams/${examId}`, session, {
    method: "DELETE",
  });
}

export async function listPpiExamSources(courseId: string, session: LoginSession) {
  return requestJson<PpiExamSource[]>(`/courses/${courseId}/ppi-exam-sources`, session);
}

export async function loadPpiCatalog(
  courseId: string,
  credentials: PpiCredentials,
  session: LoginSession,
) {
  return requestJson<PpiCatalog>(`/courses/${courseId}/ppi-exam-sources/catalog`, session, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
}

export async function importPpiExamSource(
  courseId: string,
  credentials: PpiCredentials,
  lectureId: number,
  confirmTokenSpend: boolean,
  session: LoginSession,
) {
  const result = await requestJson<{ source: PpiExamSource }>(
    `/courses/${courseId}/ppi-exam-sources/imports`,
    session,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...credentials,
        ppi_lecture_id: lectureId,
        confirm_token_spend: confirmTokenSpend,
      }),
    },
  );
  return result.source;
}

export async function downloadPracticeExamPdf(
  courseId: string,
  examId: string,
  session: LoginSession,
) {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/practice-exams/${examId}/pdf`),
    authRequestInit(session),
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "PDF download failed."));
  }
  return response.blob();
}

export async function loadPracticeExamSolutions(
  courseId: string,
  examId: string,
  session: LoginSession,
) {
  return requestJson<PracticeExamSolutionSheet>(
    `/courses/${courseId}/practice-exams/${examId}/solutions`,
    session,
  );
}

export async function downloadPracticeExamSolutionPdf(
  courseId: string,
  examId: string,
  session: LoginSession,
) {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/practice-exams/${examId}/solutions/pdf`),
    authRequestInit(session),
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "Solution PDF download failed."));
  }
  return response.blob();
}

async function requestJson<T = unknown>(
  path: string,
  session: LoginSession,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(apiUrl(path), authRequestInit(session, init));
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Practice exam request failed."));
  return payload as T;
}
