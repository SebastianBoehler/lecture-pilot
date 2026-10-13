import { useI18n } from "../../i18n/i18n";
import { DiffText } from "./DiffText";
import type { DisplayUnit } from "./sectionShape";
import { escapeLeadingBlockMarker, type WordSegment } from "./wordDiff";
import "./diff-units.css";

/** One paragraph of a section diff: kept, added, removed, or edited word by word. */
export function DiffUnitView({ unit }: { unit: DisplayUnit }) {
  const { t } = useI18n();
  if (unit.kind === "same") {
    return (
      <div className="diff-unit">
        <DiffText text={unit.text} />
      </div>
    );
  }
  if (unit.kind === "edited") {
    return (
      <div className="diff-unit" data-change="edited">
        <span className="visually-hidden">{t("courseDiff.editedText")}: </span>
        <p className="diff-words">
          {unit.words.map((segment, index) => (
            <WordSegmentView key={index} segment={segment} />
          ))}
        </p>
      </div>
    );
  }
  const Tag = unit.kind === "added" ? "ins" : "del";
  return (
    <Tag className="diff-unit" data-change={unit.kind}>
      <span className="visually-hidden">
        {t(unit.kind === "added" ? "coursePage.draft.addedText" : "coursePage.draft.removedText")}
        :{" "}
      </span>
      <DiffText text={unit.text} />
    </Tag>
  );
}

function WordSegmentView({ segment }: { segment: WordSegment }) {
  const { t } = useI18n();
  const [, lead, core, trail] = /^(\s*)([\s\S]*?)(\s*)$/.exec(segment.text) ?? ["", "", "", ""];
  const text = core ? <DiffText inline text={escapeLeadingBlockMarker(core)} /> : null;
  if (segment.kind === "same") {
    return (
      <>
        {lead}
        {text}
        {trail}
      </>
    );
  }
  const Tag = segment.kind === "added" ? "ins" : "del";
  return (
    <>
      {lead}
      <Tag className="diff-word" data-change={segment.kind}>
        <span className="visually-hidden">
          {t(
            segment.kind === "added"
              ? "coursePage.draft.addedText"
              : "coursePage.draft.removedText",
          )}
          :{" "}
        </span>
        {text}
      </Tag>
      {trail}
    </>
  );
}
