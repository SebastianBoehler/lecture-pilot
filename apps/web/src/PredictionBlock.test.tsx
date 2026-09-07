import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "./i18n";
import { PredictionBlock } from "./PredictionBlock";
import { PredictionContext } from "./predictionContext";

function show(value: React.ContextType<typeof PredictionContext> = null) {
  return render(
    <I18nProvider locale="en" setLocale={() => {}}>
      <PredictionContext.Provider value={value}>
        <PredictionBlock
          block={{ id: "guess", type: "prediction", text: "What happens on new data?", items: [] }}
          className="canvas-block"
          sourceMarker={null}
        />
      </PredictionContext.Provider>
    </I18nProvider>,
  );
}

describe("Prediction card", () => {
  it("shows a read-only professor preview without a learner context", () => {
    show();
    expect(screen.getByText("What happens on new data?")).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByText(/Students can save/)).toBeVisible();
  });
  it("saves a guess without submitting an assessment", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    show({ saved: [], loading: false, error: null, save });
    await userEvent.type(screen.getByRole("textbox"), "I expect more errors");
    await userEvent.click(screen.getByRole("button", { name: "Save prediction" }));
    expect(save).toHaveBeenCalledWith("guess", "I expect more errors");
  });
  it("allows skipping without entering an answer", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    show({ saved: [], loading: false, error: null, save });
    await userEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(save).toHaveBeenCalledWith("guess", null);
  });
  it("restores the first guess and prevents rewriting it", () => {
    show({
      saved: [
        {
          block_id: "guess",
          section_id: "intro",
          publication_version: 1,
          question: "What happens?",
          answer: "My initial guess",
          created_at: "today",
        },
      ],
      loading: false,
      error: null,
      save: vi.fn(),
    });
    expect(screen.getByText("My initial guess")).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
  it("shows save failures and preserves the draft", async () => {
    show({
      saved: [],
      loading: false,
      error: null,
      save: vi.fn().mockRejectedValue(new Error("Lecture changed")),
    });
    await userEvent.type(screen.getByRole("textbox"), "A guess");
    await userEvent.click(screen.getByRole("button", { name: "Save prediction" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Lecture changed");
    expect(screen.getByRole("textbox")).toHaveValue("A guess");
  });
});
