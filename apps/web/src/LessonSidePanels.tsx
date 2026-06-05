import { useState } from "react";

import type { Lecture } from "./types";

type ArtifactPreset = "Summary" | "Quiz" | "Code" | "Diagram";

const presets: ArtifactPreset[] = ["Summary", "Quiz", "Code", "Diagram"];

export function ArtifactsPanel() {
  const [activePreset, setActivePreset] = useState<ArtifactPreset>("Summary");

  return (
    <aside className="drawer" aria-label="Artifacts panel">
      <div className="drawer-section">
        <h2>Artifacts</h2>
        <div className="artifact-actions" aria-label="Artifact presets">
          {presets.map((preset) => (
            <button
              className={activePreset === preset ? "is-active" : undefined}
              type="button"
              aria-pressed={activePreset === preset}
              key={preset}
              onClick={() => setActivePreset(preset)}
            >
              {preset}
            </button>
          ))}
        </div>
        <ArtifactPreview preset={activePreset} />
        <KernelPlayground />
      </div>
    </aside>
  );
}

function ArtifactPreview({ preset }: { preset: ArtifactPreset }) {
  if (preset === "Quiz") {
    return <QuizArtifact />;
  }

  if (preset === "Code") {
    return (
      <article className="artifact-card code-artifact">
        <h3>Runnable code cell</h3>
        <pre>
          <code>{`function rbfKernel(x, y, gamma) {
  const distance = x.reduce((sum, value, index) => {
    return sum + (value - y[index]) ** 2;
  }, 0);
  return Math.exp(-gamma * distance);
}`}</code>
        </pre>
      </article>
    );
  }

  if (preset === "Diagram") {
    return (
      <article className="artifact-card">
        <h3>Feature map sketch</h3>
        <FeatureMapDiagram />
      </article>
    );
  }

  return (
    <article className="artifact-card">
      <h3>Generated summary</h3>
      <ul className="artifact-list">
        <li>Start with the explicit feature map view.</li>
        <li>Replace explicit coordinates with kernel evaluations.</li>
        <li>Check whether the similarity still matches the learning problem.</li>
      </ul>
    </article>
  );
}

function QuizArtifact() {
  const [answer, setAnswer] = useState<"inner-product" | "coordinates" | null>(null);

  return (
    <article className="artifact-card">
      <h3>Micro quiz</h3>
      <p>In the kernel trick, what computation does k(x, x') stand in for?</p>
      <div className="quiz-options">
        <button type="button" onClick={() => setAnswer("inner-product")}>
          Inner product
        </button>
        <button type="button" onClick={() => setAnswer("coordinates")}>
          Coordinates
        </button>
      </div>
      {answer ? (
        <p className={answer === "inner-product" ? "quiz-feedback is-correct" : "quiz-feedback"}>
          {answer === "inner-product"
            ? "Correct: it replaces the inner product after mapping into feature space."
            : "Not quite: the coordinates can stay implicit."}
        </p>
      ) : null}
    </article>
  );
}

function FeatureMapDiagram() {
  return (
    <svg className="feature-diagram" role="img" aria-label="Feature map diagram" viewBox="0 0 320 180">
      <rect className="diagram-bg" x="0" y="0" width="320" height="180" rx="8" />
      <path className="diagram-axis" d="M28 148H142M52 168V42" />
      <path className="diagram-axis" d="M188 148H298M210 168V42" />
      <path className="diagram-arrow" d="M149 90h30m-8-8 8 8-8 8" />
      <path className="diagram-curve" d="M38 128C63 76 92 155 132 62" />
      <path className="diagram-plane" d="M204 118C226 92 257 92 286 118" />
      <circle className="diagram-dot dot-a" cx="52" cy="116" r="5" />
      <circle className="diagram-dot dot-a" cx="80" cy="93" r="5" />
      <circle className="diagram-dot dot-b" cx="108" cy="124" r="5" />
      <circle className="diagram-dot dot-b" cx="126" cy="73" r="5" />
      <circle className="diagram-dot dot-a" cx="222" cy="91" r="5" />
      <circle className="diagram-dot dot-a" cx="240" cy="82" r="5" />
      <circle className="diagram-dot dot-b" cx="263" cy="136" r="5" />
      <circle className="diagram-dot dot-b" cx="283" cy="128" r="5" />
      <text className="diagram-label" x="38" y="34">input x</text>
      <text className="diagram-label" x="202" y="34">phi(x)</text>
    </svg>
  );
}

function KernelPlayground() {
  const [mode, setMode] = useState<"narrow" | "medium" | "wide">("medium");
  const descriptions = {
    narrow: "sharp local similarity; useful for tight clusters but easy to overfit.",
    medium: "balanced local similarity; enough flexibility without chasing every point.",
    wide: "smooth boundary across a broad neighborhood; useful when the signal is coarse.",
  };

  return (
    <fieldset className="artifact-card kernel-playground" aria-label="Kernel playground">
      <legend>Kernel playground</legend>
      <div className="kernel-buttons">
        <button type="button" onClick={() => setMode("narrow")}>
          Narrow kernel
        </button>
        <button type="button" onClick={() => setMode("medium")}>
          Medium kernel
        </button>
        <button type="button" onClick={() => setMode("wide")}>
          Wide kernel
        </button>
      </div>
      <div className={`kernel-strip ${mode}`} aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p>{descriptions[mode]}</p>
    </fieldset>
  );
}

export function NotesPanel({ lecture }: { lecture: Lecture }) {
  return (
    <aside className="drawer" aria-label="Lecture notes panel">
      <div className="drawer-section">
        <h2>Source notes</h2>
        <div className="source-list">
          <article>
            <span>Official LaTeX source</span>
            <strong>{lecture.materialPath ?? "courses/martius-ml/lectures/03/source.tex"}</strong>
          </article>
          <article>
            <span>Timeline gate</span>
            <strong>{lecture.date} · already unlocked</strong>
          </article>
          <article>
            <span>Attendance context</span>
            <strong>{lecture.attendance}</strong>
          </article>
        </div>
      </div>
    </aside>
  );
}
