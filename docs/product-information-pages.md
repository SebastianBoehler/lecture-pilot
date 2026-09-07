# Product information pages

The footer routes to three bilingual guides. `InfoPage.tsx` chooses the article;
`InfoArticle.tsx` owns chapter links, optional details and practical examples.
Content lives in `howItWorksContent.ts`, `learningGuideContent.ts` and
`privacyContent.ts`. Keep both languages in sync with actual product behavior.

- How it works: student and lecturer journeys, shared/private workspace diagram,
  public onboarding player and limitations.
- Learning guide: practical attempts, hints, self-explanation, independent tasks,
  spacing advice and exam self-review. Research informs design, not efficacy claims.
- Privacy: data categories, model disclosure, memory scope, analytics, operator
  access, deletion boundaries and unresolved institutional details.

Privacy facts checked 7 September 2026 against `coaching_state_io.py`,
`user_memory.py`, `learner_workspace_reset.py`, practice-exam/annotation routes,
`observability.py` and production Compose/environment: OpenAI tutor requests,
logging observability, metadata tracing, university-hosted application storage.
Provider retention is not claimed to be zero. External media contacts its provider;
the onboarding recording is served by LecturePilot itself.

Controller/contact, legal basis, complete processor/transfer details, retention,
backup expiry and formal rights procedure require institutional confirmation.
Do not replace these open items with inferred legal claims. Recheck this page when
provider, tracing, storage or deletion behavior changes.

Tests cover locale switching, chapter targets, important disclosure boundaries
and opening the real onboarding player. Verify layout and navigation in a browser.
