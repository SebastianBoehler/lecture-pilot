import { apiUrl } from "./api";
import { readApiError } from "./apiError";
import { authRequestInit } from "./authz";
import type {
  PpiCatalog,
  PpiCredentials,
  PpiExamSource,
  PracticeExam,
  PracticeExamGenerationInput,
  PracticeExamGenerationStatus,
} from "./practiceExamTypes";
import type { LoginSession } from "./types";

export async function listPracticeExams(courseId: string, session: LoginSession) {
  return requestJson<PracticeExam[]>(`/courses/${courseId}/practice-exams`, session);
}

export async function generatePracticeExam(
  courseId: string,
  input: PracticeExamGenerationInput,
  idempotencyKey: string,
  session: LoginSession,
) {
  return requestJson<PracticeExam>(`/courses/${courseId}/practice-exam-generations`, session, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(input),
  });
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
