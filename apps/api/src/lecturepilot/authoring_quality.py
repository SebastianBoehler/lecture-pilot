"""Reuse only byte-identical semantic review inputs within one authoring job."""

import asyncio
from hashlib import sha256

from lecturepilot.course_canvas_quality_prompt import quality_review_batches


class AuthoringQualityMemo:
    def __init__(self):
        self.results = {}

    async def review(self, reviewer, *, settings, source_document, candidate_document):
        source_key = source_document.model_dump_json()

        async def check(sections):
            candidate = candidate_document.model_copy(update={"sections": sections})
            key = sha256((source_key + candidate.model_dump_json()).encode()).hexdigest()
            if key not in self.results:
                self.results[key] = await reviewer.review(
                    settings=settings,
                    source_document=source_document,
                    candidate_document=candidate,
                )
            return self.results[key]

        results = await asyncio.gather(
            *(
                check(sections)
                for sections in quality_review_batches(
                    source_document,
                    candidate_document,
                )
            )
        )
        return [issue for result in results for issue in result]
