import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { InfoPage } from "./InfoPage";

it("describes the bounded private tutor context precisely", () => {
  render(<InfoPage kind="privacy" />);

  expect(
    screen.getByText(/up to eight recent learner and tutor messages from this lecture/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/ordinary private chat messages.*course analytics/i)).toBeInTheDocument();
});
