const sources = [
  {
    citation:
      "Schwerter, Lauermann, Brahm & Murayama (2025). Differential use and effectiveness of practice testing: Who benefits and who engages?",
    href: "https://doi.org/10.1016/j.lindif.2025.102761",
  },
  {
    citation:
      "Lachner, Russ, Hübner, Sibley & Scheiter (2025). When does learning by non-interactive teaching work?",
    href: "https://doi.org/10.1007/s10648-025-10060-0",
  },
  {
    citation:
      "Roelle et al. (2022). Combining retrieval practice and generative learning in educational contexts.",
    href: "https://doi.org/10.1026/0049-8637/a000261",
  },
  {
    citation:
      "Schwerter, Wortha & Gerjets (2022). E-learning with multiple-try feedback: Can hints foster students' achievement?",
    href: "https://doi.org/10.1007/s11423-022-10105-z",
  },
  {
    citation:
      "Murayama (2022). A reward-learning framework of knowledge acquisition: Curiosity, interest, and rewards.",
    href: "https://doi.org/10.1037/rev0000349",
  },
  {
    citation:
      "MeMoRAI: Motivation and metacognition in self-regulated learning with generative AI.",
    href: "https://uni-tuebingen.de/fakultaeten/wirtschafts-und-sozialwissenschaftliche-fakultaet/faecher/fachbereich-sozialwissenschaften/hector-institut-fuer-empirische-bildungsforschung/forschung/aktuelle-studien/memorai/",
  },
  {
    citation:
      "Cepeda et al. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis.",
    href: "https://doi.org/10.1037/0033-2909.132.3.354",
  },
  {
    citation: "Pashler et al. (2008). Learning styles: Concepts and evidence.",
    href: "https://doi.org/10.1111/j.1539-6053.2009.01038.x",
  },
] as const;

export function LearningScienceArticle() {
  return (
    <article className="how-article learning-science-article">
      <header className="how-hero">
        <h1>Learning how to learn</h1>
        <p>
          Most of us arrive at university with plenty to learn and very little instruction on how to
          do it. These are a few practices worth building into an ordinary week of lectures,
          exercises, and exam preparation.
        </p>
      </header>

      <section aria-labelledby="learning-start-heading">
        <h2 id="learning-start-heading">Start with a blank page</h2>
        <p>
          After a lecture, the easiest thing is to open the slides again. The second read usually
          feels smoother than the first. Unfortunately, that feeling tells you very little about
          whether you could explain the idea tomorrow or use it in an exercise. Before reopening the
          material, write down what you remember. Then compare.
        </p>
        <p>
          Jakob Schwerter and colleagues recently followed 325 first-semester mathematics students.
          Students who used more voluntary practice tests tended to do better in the exam. Yet the
          students who started out weaker used those tests less often and needed more attempts to
          make similar progress. Self-testing works best when it is a normal, low-pressure part of
          studying—not something you save for the week before the exam.
        </p>
        <PracticeLoop />
      </section>

      <section aria-labelledby="generate-heading">
        <h2 id="generate-heading">Explain it before you ask for another explanation</h2>
        <p>
          Take a definition, a derivation, or a difficult transition from the lecture and explain it
          as if a fellow student had asked you about it. You can speak, write, or sketch. The format
          matters less than having to put the pieces together yourself.
        </p>
        <p>
          Work by Andreas Lachner, Heike Russ, and colleagues in Tübingen is useful precisely
          because the result is not too neat. Students who explained material to an imagined peer
          understood more immediately than students who simply studied it again. Eight weeks later,
          however, there was no advantage across the board, and the benefit differed between
          students. Explaining is not a trick. It helps when it makes you genuinely work through the
          idea.
        </p>
      </section>

      <section aria-labelledby="feedback-heading">
        <h2 id="feedback-heading">A hint is often more useful than the solution</h2>
        <p>
          In statistics exercises studied by Schwerter, Franz Wortha, and Peter Gerjets, students
          could try again after an error and, in some cases, received a hint. That order matters. A
          hint can point you back towards the problem; a complete solution ends the attempt.
        </p>
        <p>
          When you use a tutor—human or digital—bring an attempt. Ask what went wrong or request the
          next useful clue. Only look at the full solution after you have tried to repair the answer
          yourself.
        </p>
      </section>

      <section aria-labelledby="spacing-heading">
        <h2 id="spacing-heading">Do not finish a topic in one sitting</h2>
        <p>
          Coming back to a topic can feel inefficient because some of it has already faded. That is
          also what makes the return useful: you have to retrieve the idea again instead of merely
          continuing from short-term memory. A major review covering 317 experiments found a clear
          advantage for spreading learning over time rather than packing it into one block.
        </p>
        <p>
          The right interval depends on the material and on when you need it. For a course, a useful
          starting point is a brief check the next day, another later in the week, and a cumulative
          question after that. If recall is easy, wait longer next time. If the idea has vanished,
          shorten the interval.
        </p>
      </section>

      <section aria-labelledby="motivation-heading">
        <h2 id="motivation-heading">Make the next step small enough to begin</h2>
        <p>
          Kou Murayama's research at the Hector Institute treats curiosity and interest as processes
          that change with uncertainty, progress, and reward. In other words, motivation is not a
          fixed quality that some students have and others do not.
        </p>
        <p>
          “Study machine learning” is a poor task. “Derive the update rule without looking” is a
          better one. Pick a next step that is demanding but clear enough to start: one concept, one
          representative problem, or one part of the lecture you still cannot explain.
        </p>
      </section>

      <section aria-labelledby="styles-heading">
        <h2 id="styles-heading">You do not need to discover your learning type</h2>
        <p>
          You can prefer diagrams, text, or discussion without being a fixed “visual” or “auditory”
          learner. There is no good evidence that matching all instruction to such a label improves
          learning. Use the representation that suits the subject: a diagram for anatomy, a proof
          for mathematics, pronunciation practice for a language. Adapt to what you know and where
          you get stuck, not to a type assigned by a questionnaire.
        </p>
      </section>

      <section aria-labelledby="ai-heading">
        <h2 id="ai-heading">Make AI wait for your attempt</h2>
        <p>
          If an AI writes the explanation before you have thought about the problem, you may end up
          with a good answer and very little learning. A better sequence is simple: attempt the
          question, ask for a hint, revise, and then explain the final answer back in your own
          words. Researchers at the Hector Institute are currently studying this tension in the
          MeMoRAI project: where AI support helps, and where it starts to replace self-regulated
          learning.
        </p>
        <StudyProtocol />
      </section>

      <section aria-labelledby="sources-heading">
        <h2 id="sources-heading">Sources and further reading</h2>
        <p>
          A selection of the research behind the article. The first papers grew out of work in and
          around Tübingen; the final two cover spacing and learning styles more broadly.
        </p>
        <ol className="learning-sources">
          {sources.map((source) => (
            <li key={source.href}>
              <a href={source.href} rel="noreferrer" target="_blank">
                {source.citation}
              </a>
            </li>
          ))}
        </ol>
      </section>
    </article>
  );
}

function PracticeLoop() {
  return (
    <figure className="learning-loop">
      <ol>
        <li>
          <strong>Retrieve</strong>
          <span>Close the source and produce an answer.</span>
        </li>
        <li>
          <strong>Check</strong>
          <span>Compare it with the course material.</span>
        </li>
        <li>
          <strong>Repair</strong>
          <span>Correct the gap in your own words.</span>
        </li>
        <li>
          <strong>Return</strong>
          <span>Try again after a meaningful delay.</span>
        </li>
      </ol>
      <figcaption>A study loop that works with almost any subject.</figcaption>
    </figure>
  );
}

function StudyProtocol() {
  return (
    <ol className="study-protocol" aria-label="A practical study session">
      <li>
        <strong>2 minutes</strong>
        <span>Recall what you know before opening notes.</span>
      </li>
      <li>
        <strong>15 minutes</strong>
        <span>Solve, derive, explain, or draw.</span>
      </li>
      <li>
        <strong>5 minutes</strong>
        <span>Check sources and repair mistakes.</span>
      </li>
      <li>
        <strong>1 minute</strong>
        <span>Schedule the next retrieval.</span>
      </li>
    </ol>
  );
}
