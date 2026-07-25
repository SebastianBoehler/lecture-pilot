import { renderHook, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import type { LearnerProfile, LoginSession } from "./types";
import { useLearnerProfile } from "./useLearnerProfile";

const session: LoginSession = {
  username: "student01",
  term: "Sommer 2026",
  tenant_id: "tenant-tuebingen",
  roles: ["student"],
  auth_transport: "cookie",
  csrf_token: "csrf-token-with-at-least-thirty-two-characters",
  courses: [],
};

const profile: LearnerProfile = {
  onboarding_completed: true,
  learning_goal: "understand_deeply",
  preferences: {},
  global_notes: "",
  global_files: [],
  courses: [],
};

it("keeps a loaded learner profile in memory while its route is disabled", async () => {
  const fetchMock = vi.fn(async () => json(profile));
  vi.stubGlobal("fetch", fetchMock);
  const { result, rerender } = renderHook(({ enabled }) => useLearnerProfile(session, enabled), {
    initialProps: { enabled: true },
  });
  await waitFor(() => expect(result.current.profile).toEqual(profile));

  rerender({ enabled: false });

  expect(result.current.profile).toEqual(profile);
  rerender({ enabled: true });
  await waitFor(() => expect(result.current.profile).toEqual(profile));
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

function json(payload: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  };
}
