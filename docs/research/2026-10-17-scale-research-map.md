# SCALE research map: discovery resource for LecturePilot

Reviewed 17 October 2026 after a user recommendation and accompanying social
post. Scope: live map HTML, project README, and Stanford repository. This is a
resource assessment, not a full-text review of the indexed studies.

## Sources and scope

- [Interactive research map](https://ipattis.github.io/SCALE_research/)
- [Evidence page](https://ipattis.github.io/SCALE_research/evidence.html)
- [Project and methodology](https://github.com/ipattis/SCALE_research)
- [Official Stanford SCALE repository](https://scale.stanford.edu/ai/repository)

The map is an independent project, not a Stanford-endorsed analysis. It covers
1,652 papers in a 10 October 2026 snapshot. Maps organize papers by topic,
educational need, and AI use. Filters include education level, study design,
measured outcomes, and result direction. Reading lists export as RIS or CSV.

The project reports that 154 papers (9%) provide randomized or quasi-experimental
evidence measuring learning. Technical evaluation accounts for 30%. These are
the project's abstract-based classifications, not findings independently
reproduced here. Counts describe this snapshot, not a live census of the field.

SCALE's curated tags and the map's AI-extracted evidence labels are distinct.
The extraction audit uses the same model family and is a consistency check,
not independent verification. Abstracts can underdescribe methods; labels do
not establish study quality or causal credibility.

## Relevance to LecturePilot

The following are proposed uses, not new implementation requirements:

1. **Tutor and support design.** Find studies comparing guided hints, direct
   answers, worked examples, and support removal. Check whether students later
   solve unfamiliar tasks without AI. This can inform our baseline, supported
   attempt, independent exit, and delayed review design.
2. **Assessment validity.** Find human-scored evaluations of AI feedback and
   grading. Inspect false passes, false failures, language differences, and
   rubric agreement before drawing conclusions about our checkpoint assessor.
3. **Professor authoring.** Find evaluations of generated instructional
   materials and teacher review. Distinguish artifact quality from measured
   student learning when assessing our source-backed authoring workflow.
4. **Product evaluation.** Use the collection to identify suitable comparisons
   and outcome measures. Prioritize delayed retention and independent transfer;
   keep satisfaction, engagement, and assisted completion as separate outcomes.

For the first reading pass, filter to **Post-Secondary**, **Student**, and
**Learning – Student Support** or **Teaching – Assessment and Feedback**.
Prioritize studies measuring learning with randomized or quasi-experimental
designs, while retaining relevant reviews and negative or mixed findings.
Search within this set for tutoring, scaffolding, feedback, retention, transfer,
and self-regulation. Do not assume higher-education applicability from K–12
results alone.

## Follow-up method

Export a small candidate list and deduplicate it against the
[existing bibliography](2026-09-25-learning-research-discovery-bibliography.md).
Our bibliography already includes Bastani, Kestin, and Tutor CoPilot; their
presence in a new map would not constitute new independent evidence.

For each new candidate, read the original methods and results. Record the
population, comparison, AI intervention, assistance allowed during testing,
follow-up delay, attrition, effect uncertainty, and publication status. Add
only supported implications to the
[existing evidence audit](2026-09-25-lecturepilot-evidence-audit.md).

The map can improve literature discovery. It cannot establish LecturePilot's
learning efficacy. No product changes or learner study were performed in this
review.

Follow-up completed: [seven-paper full-text comparison with current code](2026-10-17-scale-lecturepilot-comparison.md),
with separate tutoring and feedback/assessment reading notes.
