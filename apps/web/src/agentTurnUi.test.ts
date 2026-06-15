import { describe, expect, it } from "vitest";

import { appendLiveToolTag, pendingTutorMessage } from "./agentTurnUi";

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
});
