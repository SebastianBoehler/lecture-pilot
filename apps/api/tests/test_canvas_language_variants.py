import pytest

from auth_helpers import professor_headers, student_headers
from lecturepilot.canvas_language_store import CanvasLanguageStore
from lecturepilot.canvas_language_variants import (
    TeachingText,
    TranslationOutput,
    mask,
    prepare_variant,
    publish_variant,
    teaching_texts,
    validate_variant,
)
from test_quiz_learner_overlay import COURSE_ID, LECTURE_ID, _client


def _prepared(tmp_path):
    client = _client(tmp_path)
    store = CanvasLanguageStore(client.app.state.canvas_workspace.layout)
    snapshot = store.snapshot(COURSE_ID, LECTURE_ID)
    output = TranslationOutput(
        texts=[
            TeachingText(key=t.key, text=mask(t.text)[0]) for t in teaching_texts(snapshot.document)
        ]
    )
    return client, store, snapshot, output


def test_assessments_excluded_and_protected_content_exact(tmp_path):
    _, _, snapshot, output = _prepared(tmp_path)
    for section in snapshot.document.sections:
        for block in section.blocks:
            if block.type in {"checkpoint", "quiz", "component", "math"}:
                assert not any(f":{block.id}:" in t.key for t in output.texts)
    variant = prepare_variant(snapshot, "de", output)
    validate_variant(variant, snapshot)
    assert variant.published_at is None
    assert (
        publish_variant(variant, snapshot, variant.digest, "professor").published_by == "professor"
    )
    with pytest.raises(ValueError, match="draft changed"):
        publish_variant(variant, snapshot, "0" * 64, "professor")
    changed = snapshot.publication.model_copy(update={"version": snapshot.version + 1})
    from dataclasses import replace

    with pytest.raises(ValueError, match="publication changed"):
        validate_variant(variant, replace(snapshot, publication=changed))


@pytest.mark.parametrize(
    "original",
    ["Compute $x^2$ using 12 cases", "Run `f(2)`", "Read [source](https://example.com/a)"],
)
def test_translation_cannot_add_or_remove_protected_content(original):
    from lecturepilot.canvas_language_variants import restore

    masked, _ = mask(original)
    assert restore(masked, original) == original
    with pytest.raises(ValueError):
        restore(masked + " 99", original)
    with pytest.raises(ValueError):
        restore("No preserved markers", original)


def test_draft_private_publish_exact_and_stale_language_unavailable(tmp_path):
    client, store, snapshot, output = _prepared(tmp_path)
    variant = prepare_variant(snapshot, "de", output)
    store.write(COURSE_ID, LECTURE_ID, variant)
    base = f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas/languages"
    student = student_headers("student-a", course_ids=[COURSE_ID])
    professor = professor_headers()
    assert client.get(base, headers=student).json()["variants"] == []
    assert client.get(base, headers=student).json()["canonical_language"] is None
    assert client.get("/admin" + base + "/de", headers=student).status_code == 403
    assert (
        client.post(
            "/admin" + base + "/de/publish",
            headers=student,
            json={"digest": variant.digest, "assessment_language": "en"},
        ).status_code
        == 403
    )
    response = client.post(
        "/admin" + base + "/de/publish",
        headers=professor,
        json={"digest": variant.digest, "assessment_language": "en"},
    )
    assert response.status_code == 200, response.text
    result = client.get(base, headers=student).json()
    assert result["variants"][0]["digest"] == variant.digest
    assert result["canonical_language"] == "en"
    assert "published_by" not in result["variants"][0]
    assert client.get(base, headers=student_headers("outsider", course_ids=[])).status_code == 404
    path = store.path(COURSE_ID, LECTURE_ID, "de", published=True)
    path.write_text(
        variant.model_copy(
            update={"published_at": "now", "publication_binding": "stale"}
        ).model_dump_json()
    )
    assert client.get(base, headers=student).json()["unavailable_languages"] == ["de"]


def test_translation_rejects_missing_identity_and_tampered_text(tmp_path):
    _, _, snapshot, output = _prepared(tmp_path)
    with pytest.raises(ValueError, match="identities"):
        prepare_variant(snapshot, "de", output.model_copy(update={"texts": output.texts[:-1]}))
    variant = prepare_variant(snapshot, "de", output)
    variant.texts[0].text += " changed"
    with pytest.raises(ValueError, match="integrity"):
        validate_variant(variant, snapshot)


def test_language_listing_uses_one_canonical_snapshot(tmp_path, monkeypatch):
    client, store, snapshot, output = _prepared(tmp_path)
    variant = publish_variant(
        prepare_variant(snapshot, "de", output),
        snapshot,
        prepare_variant(snapshot, "de", output).digest,
        "professor",
    )
    store.write(COURSE_ID, LECTURE_ID, variant, published=True)
    calls = []

    def captured(self, course_id, lecture_id):
        calls.append((course_id, lecture_id))
        assert len(calls) == 1, (
            "Language response must not combine independently reread publications"
        )
        return snapshot

    monkeypatch.setattr(CanvasLanguageStore, "snapshot", captured)
    response = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas/languages",
        headers=student_headers("student", course_ids=[COURSE_ID]),
    )
    assert response.status_code == 200, response.text
    assert len(calls) == 1
    assert response.json()["variants"][0]["publication_version"] == snapshot.version


def test_translation_rejects_operator_change_even_when_numbers_match():
    from lecturepilot.canvas_language_variants import restore

    original = "The ratio is 48/(48+12)."
    masked, _ = mask(original)
    with pytest.raises(ValueError, match="arithmetic operator"):
        restore(masked.replace("+", "-"), original)


def test_assessment_language_is_bound_to_publication_not_course_setup(tmp_path):
    from dataclasses import replace

    _, store, snapshot, _ = _prepared(tmp_path)
    assert store.assessment_language(COURSE_ID, LECTURE_ID, snapshot) is None
    store.declare_assessment_language(COURSE_ID, LECTURE_ID, snapshot, "en", "professor")
    assert store.assessment_language(COURSE_ID, LECTURE_ID, snapshot) == "en"
    with pytest.raises(ValueError, match="differs"):
        store.declare_assessment_language(COURSE_ID, LECTURE_ID, snapshot, "de", "professor")
    newer = replace(snapshot, publication=snapshot.publication.model_copy(update={"version": 2}))
    assert store.assessment_language(COURSE_ID, LECTURE_ID, newer) is None
