import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type {
  PracticeDesign,
  PracticeDesignReadiness,
  PracticeDesignUpdate,
} from "./practiceDesignTypes";
import type { LoginSession } from "./types";

export class PracticeDesignRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "PracticeDesignRequestError";
  }
}

export async function getPracticeDesign(input: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
}): Promise<PracticeDesign> {
  return request(
    path(input.courseId, input.lectureId),
    input.session,
    undefined,
    "Practice design failed to load.",
  );
}

export async function getPracticeDesignReadiness(input: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
}): Promise<PracticeDesignReadiness> {
  const response = await fetch(
    apiUrl(`${path(input.courseId, input.lectureId)}/readiness`),
    authRequestInit(input.session),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new PracticeDesignRequestError(
      readApiError(payload, "Practice design readiness failed to load."),
      response.status,
    );
  }
  return payload as PracticeDesignReadiness;
}

export async function proposePracticeDesign(input: {
  courseId: string;
  lectureId: string;
  refresh?: boolean;
  session: LoginSession;
}): Promise<PracticeDesign> {
  const suffix = input.refresh ? "?refresh=true" : "";
  return request(
    `${path(input.courseId, input.lectureId)}/proposal${suffix}`,
    input.session,
    { method: "POST" },
    "Practice design proposal failed to generate.",
  );
}

export async function updatePracticeDesign(input: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
  update: PracticeDesignUpdate;
}): Promise<PracticeDesign> {
  return request(
    path(input.courseId, input.lectureId),
    input.session,
    json("PUT", input.update),
    "Practice design failed to save.",
  );
}

export async function approvePracticeDesign(input: {
  courseId: string;
  lectureId: string;
  design: PracticeDesign;
  session: LoginSession;
}): Promise<PracticeDesign> {
  return request(
    `${path(input.courseId, input.lectureId)}/approve`,
    input.session,
    json("POST", {
      source_revision: input.design.source_revision,
      practice_design_revision: input.design.revision,
    }),
    "Practice design approval failed.",
  );
}

export async function reviewPracticeDesign(input: {
  courseId: string;
  lectureId: string;
  design: PracticeDesign;
  session: LoginSession;
}): Promise<PracticeDesign> {
  return request(
    `${path(input.courseId, input.lectureId)}/review`,
    input.session,
    json("POST", {
      source_revision: input.design.source_revision,
      practice_design_revision: input.design.revision,
    }),
    "Practice design review failed.",
  );
}

function path(courseId: string, lectureId: string): string {
  return `/admin/courses/${courseId}/lectures/${lectureId}/practice-design`;
}

function json(method: "POST" | "PUT", body: object): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function request(
  requestPath: string,
  session: LoginSession,
  init: RequestInit | undefined,
  fallback: string,
): Promise<PracticeDesign> {
  const response = await fetch(apiUrl(requestPath), authRequestInit(session, init));
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new PracticeDesignRequestError(readApiError(payload, fallback), response.status);
  }
  return payload as PracticeDesign;
}
