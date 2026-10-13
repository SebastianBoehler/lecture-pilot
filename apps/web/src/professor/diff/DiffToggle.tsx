import type { ReactNode } from "react";

/** Disclosure button for folded diff content. */
export function DiffToggle({
  children,
  controls,
  expanded,
  onToggle,
}: {
  children: ReactNode;
  controls?: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      aria-controls={controls}
      aria-expanded={expanded}
      className="diff-toggle"
      onClick={onToggle}
      type="button"
    >
      {children}
    </button>
  );
}
