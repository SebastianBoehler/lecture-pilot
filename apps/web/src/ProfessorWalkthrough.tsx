import { useEffect } from "react";
import { EVENTS, STATUS, useJoyride, type EventData, type Step } from "react-joyride";

import { useI18n } from "./i18n";

export const PROFESSOR_WALKTHROUGH_EVENT = "lecturepilot:start-professor-walkthrough";
const PROFESSOR_WALKTHROUGH_VERSION = "v2";
const TOUR_TARGET_WAIT_MS = 2500;

type ProfessorWalkthroughView = "professor" | "course-management" | "performance";

export function ProfessorWalkthrough({
  onViewChange,
  username,
}: {
  onViewChange: (view: ProfessorWalkthroughView) => void;
  username: string;
}) {
  const { t } = useI18n();
  const { controls, Tour } = useJoyride({
    continuous: true,
    onEvent: (event) => handleTourEvent(event, username),
    options: {
      arrowColor: "var(--color-accent-primary)",
      backgroundColor: "var(--color-accent-primary)",
      blockTargetInteraction: true,
      buttons: ["back", "close", "primary", "skip"],
      closeButtonAction: "skip",
      dismissKeyAction: "close",
      offset: 14,
      overlayClickAction: false,
      overlayColor: "rgb(10 16 28 / 0.56)",
      primaryColor: "#ffffff",
      scrollOffset: 88,
      showProgress: true,
      skipBeacon: true,
      spotlightPadding: 7,
      spotlightRadius: 5,
      targetWaitTimeout: 2500,
      textColor: "var(--color-on-accent)",
      width: 360,
      zIndex: 1000,
    },
    locale: {
      back: t("tour.back"),
      close: t("tour.close"),
      last: t("tour.done"),
      next: t("tour.next"),
      nextWithProgress: t("tour.nextProgress"),
      open: t("tour.open"),
      skip: t("tour.skip"),
    },
    run: !hasSeenProfessorWalkthrough(username),
    steps: walkthroughSteps(t, onViewChange),
    styles: {
      buttonBack: {
        border: "1px solid color-mix(in srgb, var(--color-on-accent) 64%, transparent)",
        color: "var(--color-on-accent)",
      },
      buttonPrimary: {
        backgroundColor: "var(--color-on-accent)",
        borderRadius: 4,
        color: "var(--color-accent-primary)",
        fontWeight: 750,
        padding: "8px 14px",
        whiteSpace: "nowrap",
      },
      buttonSkip: { fontSize: 13, textDecoration: "underline" },
      floater: { filter: "drop-shadow(0 12px 22px rgb(0 0 0 / 0.18))" },
      tooltip: { borderRadius: 6, padding: 18 },
      tooltipContainer: { lineHeight: 1.5, textAlign: "left" },
      tooltipContent: { fontSize: 14, paddingBottom: 16, paddingTop: 8 },
      tooltipFooter: {
        borderTop: "1px solid color-mix(in srgb, var(--color-on-accent) 30%, transparent)",
        paddingTop: 12,
      },
      tooltipTitle: { fontSize: 16, fontWeight: 760 },
    },
  });

  useEffect(() => {
    const restart = () => controls.reset(true);
    window.addEventListener(PROFESSOR_WALKTHROUGH_EVENT, restart);
    return () => window.removeEventListener(PROFESSOR_WALKTHROUGH_EVENT, restart);
  }, [controls]);

  return Tour;
}

export function requestProfessorWalkthrough() {
  window.dispatchEvent(new Event(PROFESSOR_WALKTHROUGH_EVENT));
}

export function hasSeenProfessorWalkthrough(username: string) {
  return window.localStorage.getItem(walkthroughStorageKey(username)) === "seen";
}

export function walkthroughStorageKey(username: string) {
  return `lecturepilot.professor-walkthrough.${PROFESSOR_WALKTHROUGH_VERSION}.${username}`;
}

function handleTourEvent(event: EventData, username: string) {
  if (
    event.type === EVENTS.TOUR_END &&
    (event.status === STATUS.FINISHED || event.status === STATUS.SKIPPED)
  ) {
    window.localStorage.setItem(walkthroughStorageKey(username), "seen");
  }
}

function walkthroughSteps(
  t: ReturnType<typeof useI18n>["t"],
  onViewChange: (view: ProfessorWalkthroughView) => void,
): Step[] {
  return [
    {
      content: t("tour.navigation.content"),
      placement: "center",
      target: "body",
      title: t("tour.navigation.title"),
    },
    {
      before: openView("professor", '[data-tour="course-creation-workflow"]', onViewChange),
      content: t("tour.builder.content"),
      target: '[data-tour="course-creation-workflow"]',
      title: t("tour.builder.title"),
    },
    {
      before: openView(
        "course-management",
        '[data-tour="course-management-workflow"]',
        onViewChange,
      ),
      content: t("tour.manage.content"),
      target: '[data-tour="course-management-workflow"]',
      title: t("tour.manage.title"),
    },
    {
      before: openView("performance", '[data-tour="course-performance-workflow"]', onViewChange),
      content: t("tour.performance.content"),
      target: '[data-tour="course-performance-workflow"]',
      title: t("tour.performance.title"),
    },
    {
      content: t("tour.restart.content"),
      placement: "bottom-end",
      target: '[data-tour="professor-support"]',
      title: t("tour.restart.title"),
    },
  ];
}

function openView(
  view: ProfessorWalkthroughView,
  target: string,
  onViewChange: (view: ProfessorWalkthroughView) => void,
) {
  return async () => {
    onViewChange(view);
    await waitForTourTarget(target);
  };
}

function waitForTourTarget(target: string) {
  if (document.querySelector(target)) return Promise.resolve();
  return new Promise<void>((resolve) => {
    const observer = new MutationObserver(() => {
      if (!document.querySelector(target)) return;
      window.clearTimeout(timeoutId);
      observer.disconnect();
      resolve();
    });
    const timeoutId = window.setTimeout(() => {
      observer.disconnect();
      resolve();
    }, TOUR_TARGET_WAIT_MS);
    observer.observe(document.body, { childList: true, subtree: true });
  });
}
