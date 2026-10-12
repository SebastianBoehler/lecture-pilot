import { describe, expect, it } from "vitest";

import { appendLiveToolTag, completePendingTutorMessage, pendingTutorMessage } from "./agentTurnUi";

describe("agent turn UI state", () => {
  it("does not seed pending turns with placeholder tool calls", () => {
    expect(pendingTutorMessage("pending-1")).not.toHaveProperty("toolTags");
  });

  it("shows live tags only for visible tool activities", () => {
    const pending = pendingTutorMessage("pending-1");
    const hidden = appendLiveToolTag([pending], "pending-1", "call tutor model");
    expect(hidden[0].toolTags).toBeUndefined();

    const visible = appendLiveToolTag(hidden, "pending-1", "focus: detailed-bayes-decision-md");
    expect(visible[0].toolTags).toEqual(["focus: detailed-bayes-decision-md"]);
  });

  it("retains actual streamed actions after completion without duplicating returned actions", () => {
    const pending = {
      ...pendingTutorMessage("pending-1"),
      toolTags: ["read: source.md", "focus: risk"],
    };
    const [completed] = completePendingTutorMessage([pending], pending.id, {
      message: "Consider risk.",
      model: "provider/model",
      canvas_commands: [{ type: "focus_section", section_id: "risk" }],
    });
    expect(completed.toolTags).toEqual(["read: source.md", "focus: risk"]);
    expect(completed.isPending).toBeUndefined();
  });
});
