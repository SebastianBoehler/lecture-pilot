"""Reuse only byte-identical semantic review inputs within one authoring job."""

import asyncio
from hashlib import sha256

from lecturepilot.course_canvas_quality_prompt import compact_quality_evidence


class AuthoringQualityMemo:
    def __init__(self):
        self.results = {}

    async def review(self, reviewer, *, settings, source_document, candidate_document):

        async def check(section):
            candidate = candidate_document.model_copy(update={"sections": [section]})
            evidence = compact_quality_evidence(source_document, candidate)
            key = sha256((settings.model + evidence).encode()).hexdigest()
            if key not in self.results:
                self.results[key] = await reviewer.review(
                    settings=settings,
                    source_document=source_document,
                    candidate_document=candidate,
                )
            return self.results[key]

        results = await asyncio.gather(*(check(section) for section in candidate_document.sections))
        return [issue for result in results for issue in result]
