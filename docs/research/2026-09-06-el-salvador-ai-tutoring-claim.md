# El Salvador AI-tutoring claim: evidence and implementation

Checked 2026-09-06. Research only; no application changes or efficacy claims.

## Bottom line

The supplied Polymarket screenshot is a lead, not a study. The reported result
concerns participating schools in a broader education-modernization programme.
It does not establish that an AI tutor caused the result, that all Salvadoran
schools reached European averages, or that LecturePilot would achieve the same.

## What was reported, and what could be verified

- September 5 reporting attributes to the World Bank a PISA for Schools
  assessment involving 1,198 volunteer students in 171 public pilot schools,
  with performance compared to Germany and Sweden's PISA 2022 averages.
  Bukele linked it to a programme including AI tutors and said testing occurred
  in June 2026. These are reported announcements, not an inspected evaluation
  dataset. [Announcement reporting](https://diario.elmundo.sv/nacionales/bukele-destaca-resultados-comparables-con-promedios-de-suecia-y-alemania-en-prueba-pisa-a-escuelas-con-tutores-de-ia-de-prueba-piloto).
- The OECD confirms that PISA for Schools supports school-level international
  benchmarking on the PISA scale. This is not equivalent to a nationally
  representative PISA survey or an experimental evaluation of a treatment.
  El Salvador's education ministry is listed as an accredited test provider.
  [OECD programme](https://www.oecd.org/en/about/projects/pisa-for-schools.html).
- I did not locate an accessible full report for this particular pilot with
  numerical scores, confidence intervals, sampling/response details, baseline
  comparability, treatment exposure and a concurrent comparison group. Direct
  access to the cited social-media source was unsuccessful. Consequently the
  precise effect size and the causal contribution of AI remain unverified.

The comparison is not inherently invalid: the tests are intended for
benchmarking. The unsupported leap is from a selected group's benchmark score
to a causal claim about AI or a claim about the entire country. Volunteer
participation creates a selection question; it does not itself prove bias.

## What the implementation documents actually describe

A November 2025 World Bank concept document describes the modernization design:
an initial three-school proof of concept in September 2024, followed by a pilot;
curriculum-linked digital lessons alongside textbooks; teacher training and
coaching; baseline diagnostics, progress checks and a final post-test. The
platform is intended for daily teacher-guided use, with daily formative checks,
monthly assessments and annual summative assessment. Deployment includes
connectivity, devices and school support. These are design descriptions, not
verification that every element was delivered in every evaluated school.
[World Bank concept document, pp. 7–9](https://documents1.worldbank.org/curated/en/099112525170540758/pdf/P511960-cd8a6424-77e8-4d8a-9607-68f2ac9b1af9.pdf).

The March 31, 2026 approval announcement confirms AprendES targets grades 2–11,
combining structured pedagogy, remediation, teacher/principal support,
assessment systems and functioning digital infrastructure. Its US$501 million
financing supports a multi-year programme, not an AI-inference cost estimate.
It must not be divided into students to infer a tutor's API cost.
[World Bank approval](https://www.bancomundial.org/es/news/press-release/2026/03/31/banco-mundial-apoya-modernizacion-educativa-el-salvador-habilidades-ampliar-empleo).

Separately, xAI announced a Grok partnership on December 11, 2025, aiming for
over 5,000 schools over two years, with curriculum-aligned adaptive tutoring.
That announcement does not identify the exact model/configuration used by all
171 evaluated schools. I found no reproducible pilot code, prompts, retrieval
configuration, safety evaluations, deployment architecture or per-session API
cost in the inspected sources. Do not attribute the reported pilot outcome
specifically to Grok without further documentation.
[xAI announcement](https://x.ai/news/el-salvador-partnership).

## LecturePilot implications — recommendations, not new implementations

1. Treat the complete learning process as the intervention: authorized content,
   coherent teaching, student attempts, specific feedback and teacher oversight.
2. Keep supported practice performance separate from independent assessment.
   Add a delayed changed-task evaluation before claiming retained learning.
3. Automate preparation and deterministic checks, but do not equate valid JSON
   with valid mathematics, source support or effective teaching.
4. Measure costs across authoring, repairs, student sessions and teacher review;
   include failures and uncertainty, not only successful model calls.
5. Evaluate against the same course materials and comparable study time, using
   consent and institutional review as appropriate. Prefer independent/blinded
   grading and report uncertainty, attrition and prior-knowledge differences.

Existing LecturePilot authoring guidance contains capability-specific targets,
source-grounding and separation of hidden exit tasks from hints; these are
design properties, not evidence of learning efficacy. See
`apps/api/src/lecturepilot/course_teaching_instructions.py` and the
[existing learning-science brief](2026-09-04-learning-science-presentation-brief.md).
Stronger experimental precedents and implementation detail are collected in
[controlled tutoring studies](2026-09-06-ai-tutoring-controlled-studies.md).

## Presentation-safe wording

“El Salvador has reported encouraging school-level benchmark results during
a broader education-modernization pilot that includes AI tutoring. Publicly
accessible evidence reviewed here does not isolate AI's causal contribution.
Controlled tutoring studies provide more specific guidance for our design.”
