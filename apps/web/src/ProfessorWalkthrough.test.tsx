import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider, type Locale } from "./i18n";
import {
  hasSeenProfessorWalkthrough,
  ProfessorWalkthrough,
  requestProfessorWalkthrough,
  walkthroughStorageKey,
} from "./ProfessorWalkthrough";

const joyride = vi.hoisted(() => ({
  props: null as Record<string, unknown> | null,
  reset: vi.fn(),
}));

vi.mock("react-joyride", () => ({
  EVENTS: { TOUR_END: "tour:end" },
  STATUS: { FINISHED: "finished", SKIPPED: "skipped" },
  useJoyride: (props: Record<string, unknown>) => {
    joyride.props = props;
    return { controls: { reset: joyride.reset }, Tour: null };
  },
}));

describe("ProfessorWalkthrough", () => {
  beforeEach(() => {
    window.localStorage.clear();
    joyride.props = null;
    joyride.reset.mockReset();
  });

  it("auto-runs once and remembers a skipped walkthrough for that professor", () => {
    const { unmount } = renderTour("professor-one");

    expect(joyride.props?.run).toBe(true);
    act(() => {
      const onEvent = joyride.props?.onEvent as (event: Record<string, unknown>) => void;
      onEvent({ status: "skipped", type: "tour:end" });
    });
    expect(hasSeenProfessorWalkthrough("professor-one")).toBe(true);
    expect(window.localStorage.getItem(walkthroughStorageKey("professor-one"))).toBe("seen");

    unmount();
    renderTour("professor-one");
    expect(joyride.props?.run).toBe(false);
  });

  it("restarts from the first step when the persistent help action is used", () => {
    renderTour("professor-two");

    act(() => requestProfessorWalkthrough());

    expect(joyride.reset).toHaveBeenCalledWith(true);
  });

  it("uses compact action copy and keeps the progress action on one line", () => {
    renderTour("professor-three", "de");

    const locale = joyride.props?.locale as Record<string, string>;
    const options = joyride.props?.options as Record<string, string>;
    const steps = joyride.props?.steps as Array<Record<string, string>>;
    const styles = joyride.props?.styles as Record<string, Record<string, string>>;

    expect(locale.nextWithProgress).toBe("Weiter · {current}/{total}");
    expect(steps[1]).toMatchObject({
      content: "Lege den Kurs an, lade Quellen hoch, prüfe den Entwurf und veröffentliche ihn.",
      title: "Kurs erstellen",
    });
    expect(styles.buttonPrimary.whiteSpace).toBe("nowrap");
    expect(options.textColor).toBe("var(--color-on-accent)");
    expect(options.dismissKeyAction).toBe("close");
    expect(styles.buttonPrimary).toMatchObject({
      backgroundColor: "var(--color-on-accent)",
      color: "var(--color-accent-primary)",
    });
    expect(styles.buttonBack.color).toBe("var(--color-on-accent)");
  });
});

function renderTour(username: string, locale: Locale = "en") {
  return render(
    <I18nProvider locale={locale} setLocale={() => undefined}>
      <ProfessorWalkthrough username={username} />
    </I18nProvider>,
  );
}
