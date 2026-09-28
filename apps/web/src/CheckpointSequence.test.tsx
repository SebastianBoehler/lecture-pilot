import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { CheckpointDrafts } from "./CheckpointDrafts";
import { CheckpointSequence } from "./CheckpointSequence";
import { renderWithI18n } from "./test/renderWithI18n";

it("submits choice and reasoning once and clears the saved draft", async () => {
  const user = userEvent.setup();
  const submit = vi.fn(async () => undefined);
  renderWithI18n(
    <CheckpointDrafts storageKey="checkpoint-test">
      <CheckpointSequence
        block={{ id: "check", type: "checkpoint", text: "Which fits?", items: ["A", "B"] }}
        className=""
        highlightedText={null}
        sourceMarker={null}
        sectionId="section"
        onSubmitCheckpoint={submit}
        disabled={false}
      />
    </CheckpointDrafts>,
  );
  await user.click(screen.getByRole("button", { name: "B. B" }));
  await user.click(screen.getByRole("button", { name: /next/i }));
  expect(submit).not.toHaveBeenCalled();
  await user.type(screen.getByRole("textbox"), "Because of the evidence.");
  await user.click(screen.getByRole("button", { name: /submit/i }));
  expect(submit).toHaveBeenCalledExactlyOnceWith(
    "check",
    "section",
    "Selected option: B\nReasoning: Because of the evidence.",
  );
  expect(sessionStorage.getItem("checkpoint-test")).toBe("[]");
});
