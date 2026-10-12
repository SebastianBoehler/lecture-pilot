import { afterEach, describe, expect, it } from "vitest";

import { formatLectureDate } from "./lectureDate";

const originalTimeZone = process.env.TZ;

afterEach(() => {
  process.env.TZ = originalTimeZone;
});

describe("formatLectureDate", () => {
  it.each(["Pacific/Kiritimati", "Europe/Berlin", "America/Los_Angeles", "Pacific/Pago_Pago"])(
    "keeps a date-only lecture on its calendar day in %s",
    (timeZone) => {
      process.env.TZ = timeZone;

      expect(formatLectureDate("2026-08-26", "en")).toBe("Wed, 26 Aug 2026");
      expect(formatLectureDate("2026-08-26", "de")).toBe("Mi., 26. Aug. 2026");
    },
  );

  it("returns values that are not calendar dates unchanged", () => {
    expect(formatLectureDate("Draft", "en")).toBe("Draft");
    expect(formatLectureDate("2026-02-30", "en")).toBe("2026-02-30");
    expect(formatLectureDate("2026-08-26T10:00:00Z", "en")).toBe("2026-08-26T10:00:00Z");
  });
});
