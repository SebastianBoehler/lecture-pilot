import { describe, expect, it } from "vitest";
import { usageHistory } from "./usageHistoryData";

describe("usage history", () => {
  it("preserves the full period and calendar gaps instead of keeping 14 records", () => {
    const days = usageHistory({
      period_start: "2026-07-01",
      period_end: "2026-07-30",
      daily: [
        { date: "2026-07-01", tutor_turns: 4, model_requests: 8, total_tokens: 100, images: 0 },
        { date: "2026-07-30", tutor_turns: 2, model_requests: 3, total_tokens: 50, images: 0 },
      ],
    });
    expect(days).toHaveLength(30);
    expect(days[0].model_requests).toBe(8);
    expect(days[1].model_requests).toBe(0);
    expect(days[29].tutor_turns).toBe(2);
  });
});
