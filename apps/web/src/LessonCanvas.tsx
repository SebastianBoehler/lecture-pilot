import type { ReactNode } from "react";

import type { CanvasSectionId, Lecture } from "./types";

type CanvasSection = {
  id: CanvasSectionId;
  title: string;
  body: ReactNode;
};

const sections: CanvasSection[] = [
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
          The key argument is that the learning algorithm only needs inner products between mapped
          examples, not the explicit coordinates of the mapped vectors.
        </p>
      </>
    ),
  },
  {
    id: "kernel-trick",
    title: "Kernel trick",
    body: (
      <p>
        A kernel function computes <code>k(x, x')</code> directly, matching the inner product in
        feature space while avoiding an expensive explicit expansion.
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
  return (
    <article className="canvas">
      <p className="section-label">Lecture {lecture.number}</p>
      <h1>{lecture.title}</h1>
      <p className="lead">
        The official notes introduce a feature map view first, then use it to motivate kernels as
        inner products in a lifted space.
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
            <h2 id={`${section.id}-heading`}>{section.title}</h2>
            {section.body}
          </section>
        );
      })}
    </article>
  );
}
