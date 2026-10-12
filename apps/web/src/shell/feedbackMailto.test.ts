import { describe, expect, it } from "vitest";

import { buildFeedbackMailto } from "./feedbackMailto";

describe("feedback email draft", () => {
  it("prefills the category, message, and editable diagnostics", () => {
    const href = buildFeedbackMailto({
      accountType: "student",
      appVersion: "0.2.1",
      browser: "Example Browser 1.0",
      buildId: "abc123",
      category: "bug",
      courseTitle: "Machine Learning",
      lectureTitle: "Bayesian Decision Theory",
      locale: "de",
      message: "The formula did not render.",
      pageUrl: "https://lecturepilot.example/lesson",
    });
    const decoded = decodeURIComponent(href);

    expect(decoded).toContain("mailto:s.boehler@student.uni-tuebingen.de?");
    expect(decoded).toContain("subject=LecturePilot bug report");
    expect(decoded).toContain("The formula did not render.");
    expect(decoded).toContain("App version: 0.2.1");
    expect(decoded).toContain("Build: abc123");
    expect(decoded).toContain("Browser: Example Browser 1.0");
    expect(decoded).toContain("Course: Machine Learning");
    expect(decoded).toContain("Lecture: Bayesian Decision Theory");
    expect(decoded).toContain("Account type: student");
    expect(decoded).toContain("Interface language: de");
    expect(decoded).toContain("Page: https://lecturepilot.example/lesson");
  });
});
