import { GripVertical } from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { useI18n } from "./i18n";

const MIN_WIDTH = 376;
const DEFAULT_WIDTH = 436;
const MAX_WIDTH = 720;

export function sidebarWidthLimit(containerWidth: number) {
  return Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, containerWidth - 400));
}

export function useLessonSidebarWidth(layoutRef: RefObject<HTMLElement | null>) {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [maxWidth, setMaxWidth] = useState(MAX_WIDTH);
  const [dragging, setDragging] = useState(false);
  useEffect(() => {
    const measure = () => {
      if (!layoutRef.current) return;
      const max = sidebarWidthLimit(layoutRef.current.getBoundingClientRect().width);
      setMaxWidth(max);
      setWidth((current) => Math.max(MIN_WIDTH, Math.min(current, max)));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [layoutRef]);
  return {
    width,
    maxWidth,
    setWidth,
    dragging,
    setDragging,
    style: { "--lesson-sidebar-width": `${width}px` } as CSSProperties,
  };
}

export function LessonSidebarResize({
  sidebar,
}: {
  sidebar: ReturnType<typeof useLessonSidebarWidth>;
}) {
  const { t } = useI18n();
  const drag = useRef<{ x: number; width: number } | null>(null);
  const clamp = (width: number) => Math.max(MIN_WIDTH, Math.min(sidebar.maxWidth, width));
  const stop = () => {
    drag.current = null;
    sidebar.setDragging(false);
  };
  const setDragging = sidebar.setDragging;
  useEffect(
    () => () => {
      setDragging(false);
    },
    [setDragging],
  );
  return (
    <div
      className="lesson-sidebar-resize"
      role="separator"
      tabIndex={0}
      aria-label={t("sidebar.resize")}
      aria-orientation="vertical"
      aria-valuemin={MIN_WIDTH}
      aria-valuemax={sidebar.maxWidth}
      aria-valuenow={sidebar.width}
      aria-valuetext={t("sidebar.width", { width: sidebar.width })}
      title={t("sidebar.resizeHelp")}
      onDoubleClick={() => sidebar.setWidth(clamp(DEFAULT_WIDTH))}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        event.currentTarget.focus();
        event.currentTarget.setPointerCapture(event.pointerId);
        drag.current = { x: event.clientX, width: sidebar.width };
        sidebar.setDragging(true);
      }}
      onPointerMove={(event) => {
        if (drag.current)
          sidebar.setWidth(clamp(drag.current.width + drag.current.x - event.clientX));
      }}
      onPointerUp={(event) => {
        stop();
        if (event.currentTarget.hasPointerCapture(event.pointerId))
          event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onPointerCancel={stop}
      onLostPointerCapture={stop}
      onKeyDown={(event) => {
        const next =
          event.key === "ArrowLeft"
            ? sidebar.width + 20
            : event.key === "ArrowRight"
              ? sidebar.width - 20
              : event.key === "Home"
                ? MIN_WIDTH
                : event.key === "End"
                  ? sidebar.maxWidth
                  : null;
        if (next === null) return;
        event.preventDefault();
        sidebar.setWidth(clamp(next));
      }}
    >
      <GripVertical size={14} aria-hidden="true" />
    </div>
  );
}
