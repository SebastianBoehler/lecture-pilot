import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("LecturePilot app shell i18n", () => {
  it("switches the app shell between English and German", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("lecturepilot.locale", "en");
    render(<App />);

    await user.click(screen.getByRole("button", { name: /switch interface to german/i }));

    expect(screen.getByRole("heading", { name: /bei lecturepilot anmelden/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/zdv-benutzername/i)).toBeInTheDocument();
    expect(window.localStorage.getItem("lecturepilot.locale")).toBe("de");
    await waitFor(() => expect(document.documentElement.lang).toBe("de"));

    await user.click(screen.getByRole("button", { name: /oberfläche auf englisch umstellen/i }));

    expect(screen.getByRole("heading", { name: /sign in to lecturepilot/i })).toBeInTheDocument();
    expect(window.localStorage.getItem("lecturepilot.locale")).toBe("en");
    await waitFor(() => expect(document.documentElement.lang).toBe("en"));
  });
});
