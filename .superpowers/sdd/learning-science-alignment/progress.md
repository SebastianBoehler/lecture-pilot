# SDD ledger — plan: .superpowers/plans/learning-science-alignment.md

Baseline: cb8446d on feat/learning-science-alignment
Baseline verification: verify:fast passed; verify:full passed with 683 API, 22 compiler, and 259 web tests after starting isolated PostgreSQL container lecturepilot-research-test-db on 127.0.0.1:55432.

Task 1: fix round 1/5 (1 addressed, 0 open — revisionless or stale gate passes no longer satisfy a revised published gate contract; commits 9c8b1a4..0f18a41)
Task 1: complete (commits cb8446d..0f18a41, review clean)
Task 2: minor (deferred): delayed_transfer events currently set independent_attempt=false, so legacy independent_transfer_passes remains zero; revisit in Task 7 analytics redesign.
Task 2: fix round 1/5 (2 addressed, 1 open — authoritative attempt counters and once-only attendance prior fixed; emitted-assistance provenance remained open; commits 481ad6e..3ea8399)
Task 2: fix round 2/5 (1 addressed, 0 open — retry assistance is now validated against content emitted before the persisted check; commit d1a1a58)
Task 2: complete (commits 0f18a41..d1a1a58, review clean; controller-focused verification 20 passed)
Task 3: fix round 1/5 (3 addressed, 0 open — authoritative post-turn rehydration, per-identity request isolation, and durable null-gate goals; commit e2f82f5)
Task 3: complete (commits d1a1a58..e2f82f5, review clean; controller-focused verification 8 API and 16 web tests passed)
Task 4: fix round 1/5 (3 addressed, 1 open — canonical identity, terminal correction, and block-kind validation fixed; publication snapshot atomicity remained open; commit 3076f89)
Task 4: fix round 2/5 (2 addressed, 0 original open; atomic publication snapshot and document-wide canonical-ID uniqueness fixed; commit 15cde36; reviewer found learner-overlay regression)
Task 4: fix round 3/5 (1 addressed, 0 original open; learner-overlay quizzes restored under atomic publication authority; commit 23a0fc2; reviewer found migration precedence inversion)
Task 4: fix round 4/5 (1 addressed, 0 open — visible current Markdown now outranks current/legacy compiled overlays; commit e967760)
Task 4: complete (commits e2f82f5..e967760, review clean; controller-focused verification 17 API and 9 web tests passed)
Task 5: fix round 1/5 (1 addressed, 0 open — review opening now serializes current gate validation and pending binding with publication; commit 5ac0852)
Task 5: complete (commits e967760..5ac0852, review clean; controller-focused verification 8 API and 6 web tests passed)
Task 6: fix round 1/5 (5 addressed, 0 open — optimistic map revision, dirty-form approval, hook identity isolation, generation ownership, and immutable contract IDs; commit 5d0f1aa)
Task 6: complete (commits 5ac0852..5d0f1aa, review clean; controller-focused verification 13 API and 12 web tests passed)
Task 7: fix round 1/5 (4 addressed, 2 new open — learner-first headline cells, strict map-bound events, retry-safe quiz outcomes, and professor evidence metadata fixed; commit 652f2a3)
Task 7: fix round 2/5 (2 addressed, 1 new open — semantic/path event integrity and publication-bound attempt idempotency fixed; commit b0fcc9b)
Task 7: fix round 3/5 (1 addressed, 1 new open — rendered canvas snapshot became quiz version authority; commit 930b87c)
Task 7: fix round 4/5 (1 addressed, 0 open — published learner views are read-only, lock-safe in-memory snapshots; commit 15e5e5c)
Task 7: complete (commits 5d0f1aa..15e5e5c, review clean; controller-focused verification 14 API and 10 web tests passed; full final 769 API, 22 compiler, 301 web)
Task 2 deferred analytics note: resolved by Task 7 explicit delayed-transfer learner-level outcome cells; no legacy boolean-derived transfer metric remains.
Hardening gate: in progress after user directive to remove all initiative-introduced monkeypatches/test doubles, runtime legacy/compatibility paths, unnecessary fallbacks, sample/mock data, and authority bypasses before Task 8.
Hardening 1: fix round 1/5 (5 addressed, 1 new open — strict quiz state, self-contained Markdown authority, duplicate-ID GET rejection, exact schema version, and test-size splits; commit 4948ee2)
Hardening 1: fix round 2/5 (1 addressed, 0 open — non-UTF8 persisted quiz state now uses the uniform sanitized corruption boundary; commit 629b899)
Hardening 1: complete (commits 15e5e5c..629b899, review clean; controller-focused verification 15 passed; full final 795 API and 22 compiler)
Hardening 2: complete (commits 1ee883c..4460388; strict learning-map, coaching, gate-state, delayed-review, provider-result, and stream-preflight boundaries; final 761 API and 22 compiler)
Hardening gate: complete; no H3/H4 broad cleanup was pulled into Task 8.
Task 8: complete (implementation commit 245d42d; deterministic exact-draft report and acknowledgement gate, minimal coaching-bound outcome metadata, evaluation/privacy/release docs, sanitized local browser acceptance; final 767 API, 22 compiler, and 304 web tests)
