# Research-slide content and early-prototype screenshot

Content only. No PowerPoint slides created. Prepared 7 September 2026.

## Slide 3: Where I started

Use `output/presentation-assets/study-assistant-march-2025.png` (3456 × 1794).
This is an unchanged copy of `screenshots/image1.png` from the local
`study-assistant` repository, linked by its README. Git records the screenshot
addition on 30 March 2025; that is not an independently verified capture date.
It matches the user's earlier description: upload documents, generate exam
questions, answer them. `learning-app` is a separate, more developed repository.

Suggested caption: **Study Assistant — earlier prototype, 2025**.
Suggested spoken explanation: “I already had a tool that turned uploaded study
material into exam questions. LecturePilot grew from asking what else a tutor
needs to support learning.”

The screenshot contains a zero-score result panel; do not present it as evidence
of learner outcomes. Its language selector and source labels also matter: avoid
claiming multilingual output or source references first appeared in LecturePilot.
The later contribution is the instructional workflow and stronger ownership and
evidence contracts. No need to restart the old cloud-dependent application.

## Slide 5: Learning principles behind the design

Keep three short lines on screen:

- **Define the outcome before generating the lesson**
- **Ask learners to retrieve and apply**
- **Give feedback, then reduce support**

Speaker notes:

Constructive alignment connects intended outcomes with teaching activities and
assessment. This is the clearest research foundation for approving goals before
generating the canvas. Attribute the educational principle to Biggs, and the
software enforcement to LecturePilot.
[Biggs, Constructive alignment in university teaching](https://www.tru.ca/__shared/assets/Constructive_Alignment36087.pdf).

Retrieval practice provides a reason to ask students to produce an explanation
instead of only rereading one. Karpicke and Blunt's experiment found benefits
relative to elaborative concept mapping under its study conditions; it does not
establish that every quiz or every retrieval task is superior in every context.
[Karpicke & Blunt, 2011](https://pubmed.ncbi.nlm.nih.gov/21252317/).

Use the existing [learning-science brief](2026-09-04-learning-science-presentation-brief.md)
for worked examples, fading, spacing and transfer. These are distinct mechanisms;
do not collapse them into a single claim that making work harder improves learning.

Transition: “Two research connections in Tübingen make these questions especially
relevant to this project.”

## Slide 6: Research connections in Tübingen

Two items are enough for a minimal slide:

**Feedback formulation matters**
Wagner et al. · Learning and Instruction · 2024

**Rehearsal and sleep support memory consolidation**
Himmer et al. · Science Advances · 2019

Speaker notes:

Wagner, Sibley, Weiler, Burde, Scheiter and Lachner studied computer-based feedback
and physics learning across three experiments. TüCeDE's report emphasizes the
importance of feedback formulation. The connection to LecturePilot is specific:
feedback should address the learner's reasoning and support another attempt.
Neither more generated text nor a correct/incorrect label alone establishes
effective feedback.
[TüCeDE research report](https://uni-tuebingen.de/forschung/zentren-und-institute/tuebingen-center-for-digital-education/newsfullview-tuecede/article/the-more-the-better/).

Himmer et al., including researchers at Tübingen, investigated memory-system
changes using fMRI. Their study found that sleep stabilized rehearsal-related
changes in its experimental task. This is a neuroscience connection for taking
later memory seriously, rather than equating immediate fluent performance with
durable learning. It does not specify the optimal review interval for LecturePilot.
[Himmer et al., 2019, primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6482015/).

Be explicit about the level of evidence: the first is an educational feedback
study; the second investigates memory mechanisms. Neither evaluated LecturePilot.
Neither is a Martius-lab endorsement. Say the work “aligns with” a study unless
the presenter actually used it when making the earlier design decision.

Suggested closing sentence: “These findings motivate the design. Whether this
particular tool improves independent learning is the next empirical question.”

Allow approximately one minute for this second research slide. This brings the
outline to fifteen slides, about seventeen minutes of content plus transitions.
For a strict fifteen-minute slot, merge the two research slides or move the
storage/capacity slide to backup.
