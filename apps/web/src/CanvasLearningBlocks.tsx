import { useState, type ReactNode } from "react";

import { MathText } from "./MathText";
import type { CanvasBlock } from "./types";

type LearningBlockProps = {
  block: CanvasBlock;
  className: string;
  highlightedText: string | null;
  sourceMarker: ReactNode;
  onSubmitAnswer?: (block: CanvasBlock, answer: string, optionIndex: number) => void;
};

export function CheckpointBlock({
  block,
  className,
  highlightedText,
  sourceMarker,
}: LearningBlockProps) {
  return (
    <aside className={`${className} canvas-checkpoint`} id={block.id} key={block.id}>
      <div className="canvas-learning-label">{block.caption || "Checkpoint"}</div>
      <div className="canvas-markdown">
        <MathText highlightedText={highlightedText} mode="block" text={block.text ?? ""} />
      </div>
      {sourceMarker}
    </aside>
  );
}

export function QuizBlock({ block, className, onSubmitAnswer }: LearningBlockProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const correctIndex = typeof block.answer_index === "number" ? block.answer_index : null;
  return (
    <section className={`${className} canvas-quiz`} id={block.id} key={block.id}>
      <div className="canvas-learning-label">{block.caption || "Quality gate quiz"}</div>
      <div className="canvas-markdown">
        <MathText highlightedText={null} mode="block" text={block.text ?? ""} />
      </div>
      {block.items.length ? (
        <ol className="canvas-quiz-options">
          {block.items.map((item, index) => (
            <li key={item}>
              <button
                aria-label={`${optionLetter(index)} ${item}`}
                aria-pressed={selectedIndex === index}
                className={quizOptionClass(index, selectedIndex, correctIndex)}
                type="button"
                onClick={() => {
                  setSelectedIndex(index);
                  onSubmitAnswer?.(block, item, index);
                }}
              >
                <span>{optionLetter(index)}</span>
                <span className="canvas-quiz-option-text">
                  <MathText highlightedText={null} text={item} />
                </span>
                {quizResultLabel(index, selectedIndex, correctIndex) ? (
                  <span aria-hidden="true" className="canvas-quiz-result">
                    {quizResultLabel(index, selectedIndex, correctIndex)}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

export function TableBlock({
  block,
  className,
  highlightedText,
  sourceMarker,
}: LearningBlockProps) {
  const table = parseMarkdownTable(block.text ?? "");
  if (!table) {
    return (
      <pre className={`${className} canvas-table-fallback`} id={block.id} key={block.id}>
        {block.text}
        {sourceMarker}
      </pre>
    );
  }
  return (
    <figure className={`${className} canvas-table`} id={block.id} key={block.id}>
      <table>
        <thead>
          <tr>
            {table.headers.map((header) => (
              <th key={header}>
                <MathText highlightedText={highlightedText} text={header} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={`${block.id}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${block.id}-${rowIndex}-${cellIndex}`}>
                  <MathText highlightedText={highlightedText} text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {sourceMarker}
    </figure>
  );
}

function parseMarkdownTable(markdown: string) {
  const lines = markdown
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2 || !lines[0].includes("|") || !/^\|?\s*:?-{3,}/.test(lines[1])) return null;
  const headers = splitRow(lines[0]);
  const rows = lines
    .slice(2)
    .map(splitRow)
    .filter((row) => row.length);
  return { headers, rows };
}

function splitRow(line: string) {
  return line
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function optionLetter(index: number) {
  return String.fromCharCode(65 + index);
}

function quizOptionClass(index: number, selectedIndex: number | null, correctIndex: number | null) {
  if (selectedIndex === null) return "";
  if (correctIndex === index) return "is-correct";
  if (selectedIndex === index) return correctIndex === null ? "is-selected" : "is-incorrect";
  return "";
}

function quizResultLabel(index: number, selectedIndex: number | null, correctIndex: number | null) {
  if (selectedIndex === null || correctIndex === null) return null;
  if (correctIndex === index) return "Correct";
  if (selectedIndex === index) return "Review";
  return null;
}
