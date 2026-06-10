import { afterEach, expect, it, vi } from "vitest";

import { sendAgentTurnStream } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

it("emits tutor activity tags while reading the streamed agent turn", async () => {
  const encoder = new TextEncoder();
  const fetchMock = vi.fn(async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(`${JSON.stringify({ type: "activity", tag: "call tutor model" })}\n`));
          controller.enqueue(encoder.encode(`${JSON.stringify({ type: "activity", tag: "save quality gate" })}\n`));
          controller.enqueue(encoder.encode(`${JSON.stringify({ type: "result", result: streamResult() })}\n`));
          controller.close();
        },
      }),
      { status: 200 },
    ),
  );
  vi.stubGlobal("fetch", fetchMock);

  const activityTags: string[] = [];
  const result = await sendAgentTurnStream(streamInput(), {
    onActivity: (tag) => activityTags.push(tag),
  });

  expect(activityTags).toEqual(["call tutor model", "save quality gate"]);
  expect(result.message).toBe("Streamed tutor answer.");
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/agent/turn/stream"),
    expect.objectContaining({ method: "POST" }),
  );
});

function streamInput() {
  return {
    user_id: "student01",
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    attendance: "present" as const,
    message: "Check my answer.",
    canvas_state: { focused_section_id: "bayes-formula" },
  };
}

function streamResult() {
  return {
    message: "Streamed tutor answer.",
    canvas_commands: [{ type: "focus_section", section_id: "bayes-formula" }],
    quality_gate: {
      gate_id: "bayes-decision-check",
      status: "needs_evidence",
      reason: "Needs more evidence.",
    },
    model: "local-guided-preview",
  };
}
