import type { ReactNode } from "react";
import { useEffect } from "react";

import type { CanvasSectionId, Lecture } from "./types";

type CanvasSection = {
  id: CanvasSectionId;
  title: string;
  body: ReactNode;
};

const sections: CanvasSection[] = [
  {
    id: "learning-goals",
    title: "Learning goals",
    body: (
      <>
        <p>
          By the end of this lecture, the learner should be able to explain why kernels
          are useful, identify when a feature map is only implicit, and choose a valid
          kernel for a simple similarity problem.
        </p>
        <ul className="goal-list">
          <li>Connect feature maps to linear models in a lifted representation.</li>
          <li>Use inner products to avoid constructing the lifted coordinates.</li>
          <li>Check whether a proposed kernel fits the learning problem.</li>
        </ul>
      </>
    ),
  },
  {
    id: "feature-maps",
    title: "Feature maps",
    body: (
      <>
        <p>
          A feature map <code>phi(x)</code> transforms input data into a representation where simple
          linear methods can express richer decision boundaries.
        </p>
        <p className="highlighted">
          The important move is not the drawing of a higher-dimensional space. It is the
          claim that the classifier becomes linear after the representation changes.
        </p>
      </>
    ),
  },
  {
    id: "kernel-trick",
    title: "Kernel trick",
    body: (
      <>
        <p>
          A kernel function computes <code>k(x, x')</code> directly, matching the inner product in
          feature space while avoiding an expensive explicit expansion.
        </p>
        <p className="highlighted">
          The algorithm only needs inner products between mapped examples, not the explicit
          coordinates of the mapped vectors.
        </p>
      </>
    ),
  },
  {
    id: "skill-check",
    title: "Skill check",
    body: (
      <>
        <p>
          A good tutor turn should test the active learning goal before moving on. For this lecture,
          the check is whether the learner can map a concrete question to the right representation.
        </p>
        <ol className="skill-list">
          <li>State what object <code>k(x, x')</code> replaces.</li>
          <li>Explain why this saves computation for a high-dimensional map.</li>
          <li>Give one situation where the kernel view is the wrong tool.</li>
        </ol>
      </>
    ),
  },
  {
    id: "failure-mode",
    title: "Common failure mode",
    body: (
      <p>
        The common mistake is saying that kernels make nonlinear problems easy by magic. The
        precise claim is narrower: the model is linear in feature space, and the kernel lets the
        algorithm access the needed inner products there.
      </p>
    ),
  },
];

export function LessonCanvas({
  lecture,
  focusedSectionId,
}: {
  lecture: Lecture;
  focusedSectionId: CanvasSectionId;
}) {
  useEffect(() => {
    const section = document.getElementById(focusedSectionId);
    if (typeof section?.scrollIntoView !== "function") {
      return;
    }
    section.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [focusedSectionId]);

  return (
    <article className="canvas">
      <p className="section-label">Lecture {lecture.number}</p>
      <h1>{lecture.title}</h1>
      <p className="lead">
        The official notes introduce a feature-map view first, then use it to motivate kernels as
        inner products in a lifted space. The tutor can focus goals, concepts, checks, or failure
        modes depending on the learner turn.
      </p>
      {sections.map((section) => {
        const isFocused = focusedSectionId === section.id;
        return (
          <section
            aria-current={isFocused ? "true" : undefined}
            aria-labelledby={`${section.id}-heading`}
            className={isFocused ? "canvas-section is-focused" : "canvas-section"}
            id={section.id}
            key={section.id}
          >
            {isFocused ? <span className="focus-chip">In focus</span> : null}
            <h2 id={`${section.id}-heading`}>{section.title}</h2>
            {section.body}
          </section>
        );
      })}
    </article>
  );
}
