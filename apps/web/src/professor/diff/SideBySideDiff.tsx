import { useId, useState } from "react";

import { useI18n } from "../../i18n/i18n";
import type { UnitDiff } from "../canvasSectionDiff";
import { DiffToggle } from "./DiffToggle";
import { DiffUnitView } from "./DiffUnitView";

/** Paragraphs shown per column before the rest of a long rewritten section is folded. */
const PREVIEW = 4;

/** Rewritten section: the published and the draft text next to each other (stacked when narrow). */
export function SideBySideDiff({ units }: { units: readonly UnitDiff[] }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const id = useId();
  const before = units.filter((unit) => unit.kind !== "added");
  const after = units.filter((unit) => unit.kind !== "removed");
  const long = Math.max(before.length, after.length) > PREVIEW + 1;
  const shown = (column: readonly UnitDiff[]) =>
    long && !open ? column.slice(0, PREVIEW) : column;
  return (
    <div className="section-diff-body">
      <div className="diff-columns" id={id}>
        {(
          [
            ["before", before],
            ["after", after],
          ] as const
        ).map(([side, column]) => (
          <section aria-labelledby={`${id}-${side}`} className="diff-column" key={side}>
            <h5 data-side={side} id={`${id}-${side}`}>
              {t(side === "before" ? "courseDiff.before" : "courseDiff.after")}
            </h5>
            {shown(column).map((unit, index) => (
              <DiffUnitView key={index} unit={unit} />
            ))}
          </section>
        ))}
      </div>
      {long ? (
        <div className="diff-folded">
          <DiffToggle controls={id} expanded={open} onToggle={() => setOpen(!open)}>
            {open ? t("courseDiff.showLess") : t("courseDiff.showFullSection")}
          </DiffToggle>
        </div>
      ) : null}
    </div>
  );
}
