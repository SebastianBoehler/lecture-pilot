import { describe, expect, it } from "vitest";

import { materialSelectionSummary } from "./materialSelectionSummary";

describe("materialSelectionSummary", () => {
  it("summarizes folder uploads without exposing a raw extension inventory", () => {
    const tex = new File([""], "Lecture01-eng.tex", { type: "application/x-tex" });
    Object.defineProperty(tex, "webkitRelativePath", { value: "course/Lecture01-eng.tex" });
    const pdf = new File([""], "Lecture01-eng.pdf", { type: "application/pdf" });
    Object.defineProperty(pdf, "webkitRelativePath", { value: "course/Lecture01-eng.pdf" });

    expect(materialSelectionSummary([tex, pdf])).toBe("Folder: course · 2 files");
  });
});
