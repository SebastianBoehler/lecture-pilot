import { useState } from "react";

type FocusProps = {
  focused: boolean;
};

const videoCheckpoints = [
  { label: "Kernel trick", time: "28:56", seconds: 1736 },
  { label: "Designing feature vectors", time: "1:17:03", seconds: 4623 },
];

function blockClass(isFocused: boolean) {
  return isFocused ? "artifact-card is-focused" : "artifact-card";
}

export function SourcePacketBlock({ focused }: FocusProps) {
  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="source-packet-heading"
      className={blockClass(focused)}
      id="source-packet"
    >
      <h2 id="source-packet-heading">Course source packet</h2>
      <p>
        This lesson document is assembled from the lecture LaTeX notes, a figure asset, a short
        code cell, and one video selected by the media discovery pipeline. Private course files
        stay outside git.
      </p>
      <div className="source-grid">
        <span>notes/lecture-03-kernels.tex</span>
        <span>figures/feature-map-lift.pdf</span>
        <span>snippets/rbf-kernel.js</span>
        <span>video/cs229-kernels.discovery.json</span>
      </div>
    </article>
  );
}

export function ConceptCounterBlock({ focused }: FocusProps) {
  const [count, setCount] = useState(2);

  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="artifact-counter-heading"
      className={`${blockClass(focused)} concept-counter`}
      id="artifact-counter"
    >
      <h2 id="artifact-counter-heading">Concept counter</h2>
      <p>Check count: {count}</p>
      <button type="button" onClick={() => setCount((current) => current + 1)}>
        Record another check
      </button>
    </article>
  );
}

export function SummaryBlock({ focused }: FocusProps) {
  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="artifact-summary-heading"
      className={blockClass(focused)}
      id="artifact-summary"
    >
      <h2 id="artifact-summary-heading">Generated summary</h2>
      <ul className="artifact-list">
        <li>Start with the explicit feature-map view.</li>
        <li>Replace explicit coordinates with kernel evaluations.</li>
        <li>Check whether the similarity still matches the learning problem.</li>
      </ul>
    </article>
  );
}

export function QuizBlock({ focused }: FocusProps) {
  const [answer, setAnswer] = useState<"inner-product" | "coordinates" | null>(null);

  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="artifact-quiz-heading"
      className={blockClass(focused)}
      id="artifact-quiz"
    >
      <h2 id="artifact-quiz-heading">Micro quiz</h2>
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

export function CodeBlock({ focused }: FocusProps) {
  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="artifact-code-heading"
      className={`${blockClass(focused)} code-artifact`}
      id="artifact-code"
    >
      <h2 id="artifact-code-heading">Runnable code cell</h2>
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

export function DiagramBlock({ focused }: FocusProps) {
  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="artifact-diagram-heading"
      className={blockClass(focused)}
      id="artifact-diagram"
      role="region"
    >
      <h2 id="artifact-diagram-heading">Feature map diagram</h2>
      <FeatureMapDiagram />
    </article>
  );
}

export function ProfessorVideoBlock({ focused }: FocusProps) {
  const [startSeconds, setStartSeconds] = useState(1736);

  return (
    <article
      aria-current={focused ? "true" : undefined}
      aria-labelledby="artifact-video-heading"
      className={`${blockClass(focused)} youtube-artifact`}
      id="artifact-video"
    >
      <h2 id="artifact-video-heading">Professor-selected video</h2>
      <p>
        Selected as a workspace pre-asset: Stanford CS229 Lecture 7, used here for a second pass on
        the kernel trick and feature-vector design.
      </p>
      <div className="youtube-frame">
        <iframe
          title="Stanford CS229 kernels video"
          src={`https://www.youtube-nocookie.com/embed/8NYoQiRANpg?start=${startSeconds}`}
          allow="accelerometer; encrypted-media; picture-in-picture"
          allowFullScreen
        />
      </div>
      <div className="checkpoint-list" aria-label="Video checkpoints">
        {videoCheckpoints.map((checkpoint) => (
          <button
            key={checkpoint.seconds}
            type="button"
            onClick={() => setStartSeconds(checkpoint.seconds)}
          >
            {checkpoint.time} · {checkpoint.label}
          </button>
        ))}
      </div>
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

export function KernelPlayground({ focused }: FocusProps) {
  const [mode, setMode] = useState<"narrow" | "medium" | "wide">("medium");
  const descriptions = {
    narrow: "sharp local similarity; useful for tight clusters but easy to overfit.",
    medium: "balanced local similarity; enough flexibility without chasing every point.",
    wide: "smooth boundary across a broad neighborhood; useful when the signal is coarse.",
  };

  return (
    <fieldset
      aria-current={focused ? "true" : undefined}
      className={`${blockClass(focused)} kernel-playground`}
      id="artifact-playground"
      aria-label="Kernel playground"
    >
      <legend>Kernel playground</legend>
      <div className="kernel-buttons">
        <button type="button" onClick={() => setMode("narrow")}>Narrow kernel</button>
        <button type="button" onClick={() => setMode("medium")}>Medium kernel</button>
        <button type="button" onClick={() => setMode("wide")}>Wide kernel</button>
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
