import { useId, useState } from "react";

import { useI18n } from "../../i18n/i18n";
import { collapseUnchanged, type SkippedUnits, type UnitDiff } from "../canvasSectionDiff";
import { DiffToggle } from "./DiffToggle";
import { DiffUnitView } from "./DiffUnitView";
import { pairEdits, type DisplayUnit } from "./sectionShape";

/** Lightly edited section: paragraphs in place, word changes marked, unchanged runs folded. */
export function InlineSectionDiff({ units }: { units: readonly UnitDiff[] }) {
  return (
    <div className="section-diff-body">
      {collapseUnchanged(pairEdits(units)).map((unit, index) =>
        unit.kind === "skipped" ? (
          <FoldedParagraphs key={index} run={unit} />
        ) : (
          <DiffUnitView key={index} unit={unit} />
        ),
      )}
    </div>
  );
}

function FoldedParagraphs({ run }: { run: SkippedUnits<DisplayUnit> }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const id = useId();
  const count = run.units.length;
  return (
    <div className="diff-folded">
      <DiffToggle controls={id} expanded={open} onToggle={() => setOpen(!open)}>
        {count === 1 ? t("coursePage.draft.skippedOne") : t("coursePage.draft.skipped", { count })}
      </DiffToggle>
      <div className="diff-folded-content" hidden={!open} id={id}>
        {open ? run.units.map((unit, index) => <DiffUnitView key={index} unit={unit} />) : null}
      </div>
    </div>
  );
}
