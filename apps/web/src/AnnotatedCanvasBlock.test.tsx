import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AnnotatedCanvasBlock } from "./AnnotatedCanvasBlock";
import { CanvasAnnotationContext } from "./canvasAnnotationContext";
import { I18nProvider } from "./i18n";

describe("saved canvas comments", () => {
  it("opens a passage comment from its marker and reports deletion failures", async () => {
    const remove = vi.fn().mockRejectedValue(new Error("Deletion failed"));
    render(
      <I18nProvider locale="en" setLocale={vi.fn()}>
        <CanvasAnnotationContext.Provider
          value={{
            remove,
            annotations: [
              {
                id: "note-1",
                block_id: "block",
                section_id: "section",
                publication_version: 1,
                quote: "**discrete** label",
                comment: "Think of digit categories.",
                created_at: "2026-09-06",
              },
            ],
          }}
        >
          <AnnotatedCanvasBlock blockId="block">
            <p>Classification predicts a discrete label.</p>
          </AnnotatedCanvasBlock>
        </CanvasAnnotationContext.Provider>
      </I18nProvider>,
    );
    expect(screen.getByText("Think of digit categories.")).not.toBeVisible();
    await userEvent.click(screen.getByLabelText("Open comments (1)"));
    expect(screen.getByText("Think of digit categories.")).toBeVisible();
    expect(screen.getByText("discrete").tagName).toBe("STRONG");
    await userEvent.click(screen.getByRole("button", { name: "Delete comment" }));
    expect(remove).toHaveBeenCalledWith("note-1");
    expect(await screen.findByRole("alert")).toHaveTextContent("Deletion failed");
  });
});
