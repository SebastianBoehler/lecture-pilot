import { X } from "lucide-react";
import { useCallback, useEffect, useRef } from "react";

import { useI18n } from "./i18n";

const MOBILE_DRAWER_QUERY = "(max-width: 860px)";
const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function LessonDrawerClose({
  returnFocusId,
  onClose,
}: {
  returnFocusId: string;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  const closeDrawer = useCallback(() => {
    onCloseRef.current();
    window.setTimeout(() => document.getElementById(returnFocusId)?.focus(), 0);
  }, [returnFocusId]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    if (!window.matchMedia(MOBILE_DRAWER_QUERY).matches) return undefined;

    const button = buttonRef.current;
    const drawer = button?.closest<HTMLElement>(".drawer");
    if (!button || !drawer) return undefined;

    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "true");
    button.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(
        drawer?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? [],
      ).filter((element) => element.getAttribute("aria-hidden") !== "true");
      if (!focusable.length) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    drawer.addEventListener("keydown", handleKeyDown);
    return () => {
      drawer.removeEventListener("keydown", handleKeyDown);
      drawer.removeAttribute("role");
      drawer.removeAttribute("aria-modal");
    };
  }, [closeDrawer]);

  return (
    <button
      aria-label={t("lesson.closePanel")}
      className="drawer-close-button"
      ref={buttonRef}
      title={t("lesson.closePanel")}
      type="button"
      onClick={closeDrawer}
    >
      <X aria-hidden="true" size={18} />
    </button>
  );
}
