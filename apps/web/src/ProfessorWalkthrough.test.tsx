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

  it("moves through the real professor workflow in five short steps", async () => {
    const onViewChange = vi.fn();
    renderTour("professor-flow", "en", onViewChange);
    mountTourTargets();

    const steps = joyride.props?.steps as Array<Record<string, unknown>>;

    expect(steps).toHaveLength(5);
    expect(steps[0]).toMatchObject({
      placement: "center",
      target: "body",
      title: "From material to student learning",
    });

    await (steps[1].before as () => Promise<void>)();
    expect(onViewChange).toHaveBeenLastCalledWith("professor");
    expect(steps[1].target).toBe('[data-tour="course-creation-workflow"]');

    await (steps[2].before as () => Promise<void>)();
    expect(onViewChange).toHaveBeenLastCalledWith("course-management");
    expect(steps[2].target).toBe('[data-tour="course-management-workflow"]');

    await (steps[3].before as () => Promise<void>)();
    expect(onViewChange).toHaveBeenLastCalledWith("performance");
    expect(steps[3].target).toBe('[data-tour="course-performance-workflow"]');

    expect(steps[4].target).toBe('[data-tour="professor-support"]');
  });

  it("uses compact action copy and keeps the progress action on one line", () => {
    renderTour("professor-three", "de");

    const locale = joyride.props?.locale as Record<string, string>;
    const options = joyride.props?.options as Record<string, string>;
    const steps = joyride.props?.steps as Array<Record<string, unknown>>;
    const styles = joyride.props?.styles as Record<string, Record<string, string>>;

    expect(locale.nextWithProgress).toBe("Weiter · {current}/{total}");
    expect(steps[1]).toMatchObject({
      content:
        "Definiere den Kurs, lade Material hoch, prüfe erzeugte Vorlesungen in der Lernendenansicht und veröffentliche erst, wenn alles bereit ist.",
      title: "Erstellen und veröffentlichen",
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

function renderTour(
  username: string,
  locale: Locale = "en",
  onViewChange: (view: "professor" | "course-management" | "performance") => void = () => undefined,
) {
  return render(
    <I18nProvider locale={locale} setLocale={() => undefined}>
      <ProfessorWalkthrough username={username} onViewChange={onViewChange} />
    </I18nProvider>,
  );
}

function mountTourTargets() {
  const targets = [
    "course-creation-workflow",
    "course-management-workflow",
    "course-performance-workflow",
  ];
  targets.forEach((target) => {
    const node = document.createElement("div");
    node.dataset.tour = target;
    document.body.appendChild(node);
  });
}
