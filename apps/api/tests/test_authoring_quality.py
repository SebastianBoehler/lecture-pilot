from lecturepilot.authoring_quality import AuthoringQualityMemo
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from test_authoring_job import authoring_job


async def test_changed_batch_is_reviewed_but_unchanged_batch_is_reused(tmp_path):
    job = authoring_job(tmp_path)
    first = job.source.sections[0].model_copy(deep=True)
    first.blocks[0].text *= 400
    second = first.model_copy(deep=True, update={"id": "second", "source_ref": "second.md"})
    source = job.source.model_copy(update={"sections": [first, second]})
    candidate = job.source.model_copy(
        update={
            "sections": [
                job.source.sections[0],
                job.source.sections[0].model_copy(
                    deep=True, update={"id": "second", "source_ref": "second.md"}
                ),
            ]
        }
    )
    calls = []

    class Client:
        async def complete_review(self, **kwargs):
            calls.append(kwargs["candidate_document"].sections[0].id)
            return {"issues": []}

    reviewer = CanvasQualityReviewer(Client())
    memo = AuthoringQualityMemo()
    await memo.review(
        reviewer, settings=job.settings, source_document=source, candidate_document=candidate
    )
    changed = candidate.model_copy(deep=True)
    changed.sections[0].blocks[0].text += " Changed explanation."
    await memo.review(
        reviewer, settings=job.settings, source_document=source, candidate_document=changed
    )
    assert calls == ["topic", "second", "topic"]
