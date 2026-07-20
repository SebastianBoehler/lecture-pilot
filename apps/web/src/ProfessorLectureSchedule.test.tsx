import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorLectureSchedule } from "./ProfessorLectureSchedule";
import type { LectureScheduleItem } from "./types";

const initialSchedule: LectureScheduleItem[] = [
  { number: "01", title: "Foundations", date: "2026-04-15", material_path: "Lecture01.tex" },
  { number: "02", title: "Regression", date: "2026-04-22", material_path: "Lecture02.tex" },
  { number: "03", title: "Clustering", date: "2026-04-29", material_path: "Lecture03.tex" },
];

describe("ProfessorLectureSchedule ordering", () => {
  it("reorders rows by drag and drop and immediately renumbers them", () => {
    renderSchedule();

    const dataTransfer = {
      effectAllowed: "none",
      getData: vi.fn(() => "0"),
      setData: vi.fn(),
    };
    fireEvent.dragStart(screen.getByRole("button", { name: "Drag lecture 01 to reorder" }), {
      dataTransfer,
    });
    fireEvent.dragOver(screen.getAllByRole("listitem")[2], { dataTransfer });
    fireEvent.drop(screen.getAllByRole("listitem")[2], { dataTransfer });

    expect(screen.getAllByLabelText("Title").map((input) => input.getAttribute("value"))).toEqual([
      "Regression",
      "Clustering",
      "Foundations",
    ]);
    expect(screen.getAllByLabelText("No.").map((input) => input.getAttribute("value"))).toEqual([
      "01",
      "02",
      "03",
    ]);
  });

  it("offers accessible move controls", () => {
    renderSchedule();

    fireEvent.click(screen.getByRole("button", { name: "Move lecture 03 up" }));

    expect(screen.getAllByLabelText("Title").map((input) => input.getAttribute("value"))).toEqual([
      "Foundations",
      "Clustering",
      "Regression",
    ]);
    expect(
      screen.getByText("Drag rows to change their order. Numbers update automatically."),
    ).toBeVisible();
  });

  it("ignores drops that did not start from a schedule handle", () => {
    renderSchedule();

    fireEvent.drop(screen.getAllByRole("listitem")[2], {
      dataTransfer: { getData: vi.fn(() => "") },
    });

    expect(screen.getAllByLabelText("Title").map((input) => input.getAttribute("value"))).toEqual([
      "Foundations",
      "Regression",
      "Clustering",
    ]);
  });
});

function renderSchedule() {
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <ScheduleHarness />
    </I18nProvider>,
  );
}

function ScheduleHarness() {
  const [schedule, setSchedule] = useState(initialSchedule);
  return (
    <ProfessorLectureSchedule
      disabled={false}
      isApplying={false}
      onApply={vi.fn()}
      onChange={setSchedule}
      schedule={schedule}
    />
  );
}
