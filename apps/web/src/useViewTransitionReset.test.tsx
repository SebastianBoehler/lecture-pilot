import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import type { View } from "./types";
import { useViewTransitionReset } from "./useViewTransitionReset";

function ViewHarness({ view }: { view: View }) {
  useViewTransitionReset(view);
  return (
    <main>
      <h1>{view}</h1>
    </main>
  );
}

it("resets scroll and moves focus to the new page heading", () => {
  const scrollDescriptor = Object.getOwnPropertyDescriptor(window, "scrollY");
  const scrollTo = vi.fn();
  vi.stubGlobal("scrollTo", scrollTo);
  Object.defineProperty(window, "scrollY", { configurable: true, value: 640 });

  try {
    const { rerender } = render(<ViewHarness view="dashboard" />);
    rerender(<ViewHarness view="lesson" />);

    expect(scrollTo).toHaveBeenLastCalledWith({ behavior: "auto", left: 0, top: 0 });
    expect(screen.getByRole("heading", { name: "lesson" })).toHaveFocus();
  } finally {
    if (scrollDescriptor) Object.defineProperty(window, "scrollY", scrollDescriptor);
  }
});
