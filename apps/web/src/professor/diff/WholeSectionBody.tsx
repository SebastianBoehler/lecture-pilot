import { useId, useState } from "react";

import { useI18n } from "../../i18n/i18n";
import type { UnitDiff } from "../canvasSectionDiff";
import { DiffText } from "./DiffText";
import { DiffToggle } from "./DiffToggle";

/** Paragraphs shown before a long added or removed section is folded. */
const PREVIEW = 2;

/**
 * Content of an added, removed or unchanged section. The article already says which, so paragraphs
 * carry no per-paragraph marks. Unchanged sections start folded; long ones show a preview.
 */
export function WholeSectionBody({
  folded,
  units,
}: {
  folded: boolean;
  units: readonly UnitDiff[];
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const id = useId();
  const long = units.length > PREVIEW + 1;
  if (!folded && !long) {
    return (
      <div className="section-diff-body">
        {units.map((unit, index) => (
          <div className="diff-unit" key={index}>
            <DiffText text={unit.text} />
          </div>
        ))}
      </div>
    );
  }
  const shown = open ? units : folded ? [] : units.slice(0, PREVIEW);
  const label = folded
    ? t(open ? "courseDiff.hideContent" : "courseDiff.showContent")
    : open
      ? t("courseDiff.showLess")
      : t("courseDiff.showAll", { count: units.length });
  return (
    <div className="section-diff-body" data-folded={folded && !open ? "" : undefined}>
      <div id={id}>
        {shown.map((unit, index) => (
          <div className="diff-unit" key={index}>
            <DiffText text={unit.text} />
          </div>
        ))}
      </div>
      <div className="diff-folded">
        <DiffToggle controls={id} expanded={open} onToggle={() => setOpen(!open)}>
          {label}
        </DiffToggle>
      </div>
    </div>
  );
}
