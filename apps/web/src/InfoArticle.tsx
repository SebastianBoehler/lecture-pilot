import type { ReactNode } from "react";
import { useI18n } from "./i18n";
import type { InfoArticleContent } from "./infoArticleTypes";
import "./info-article.css";

export function InfoArticle({
  content,
  children,
  afterSection,
}: {
  content: InfoArticleContent;
  children?: ReactNode;
  afterSection?: Record<string, ReactNode>;
}) {
  const { locale } = useI18n();
  const de = locale === "de";
  return (
    <article className="how-article guide-article">
      <header className="how-hero">
        <h1>{content.title}</h1>
        <p>{content.intro}</p>
      </header>
      <nav className="guide-nav" aria-label={de ? "Auf dieser Seite" : "On this page"}>
        {content.sections.map((section) => (
          <a key={section.id} href={`#${section.id}`}>
            {section.title}
          </a>
        ))}
      </nav>
      {content.sections.map((section) => (
        <section key={section.id} id={section.id} aria-labelledby={`${section.id}-heading`}>
          <h2 id={`${section.id}-heading`}>{section.title}</h2>
          {section.paragraphs.map((p) => (
            <p key={p}>{p}</p>
          ))}
          {section.steps && (
            <ol className="guide-steps">
              {section.steps.map((step, index) => (
                <li key={step}>
                  <span aria-hidden="true">{index + 1}</span>
                  <p>{step}</p>
                </li>
              ))}
            </ol>
          )}
          {section.example && (
            <aside className="guide-example">
              <strong>{de ? "In LecturePilot ausprobieren" : "Try this in LecturePilot"}</strong>
              <p>{section.example}</p>
            </aside>
          )}
          {section.detail && (
            <details className="guide-detail">
              <summary>{de ? "Mehr dazu" : "More detail"}</summary>
              <p>{section.detail}</p>
            </details>
          )}
          {afterSection?.[section.id]}
        </section>
      ))}
      {children}
    </article>
  );
}
