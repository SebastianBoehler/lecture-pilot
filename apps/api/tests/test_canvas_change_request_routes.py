import asyncio
import time

from auth_helpers import professor_headers
from canvas_change_test_helpers import (
    CHANGE,
    ScriptedProvider,
    change_headers,
    drafted_client,
    lecture_state,
    publish,
    section_files,
)
from lecturepilot.authoring.canvas_change_authoring import (
    GOALS_CHANGE_MESSAGE,
    CanvasChangeRequestError,
)

INSTRUCTION = "  Add a worked example on the inner product after the explanation.  "


def test_named_section_changes_and_every_other_section_file_is_byte_identical(
    tmp_path, monkeypatch
):
    provider = ScriptedProvider()
    client = drafted_client(tmp_path, monkeypatch, provider)
    options = client.get(CHANGE, headers=professor_headers())
    assert options.status_code == 200, options.text
    assert options.json()["base"] == "draft" and options.json()["latest"] is None
    sections = options.json()["sections"]
    assert len(sections) >= 2
    before = section_files(client)

    changed = client.post(
        CHANGE,
        headers=change_headers("change-named-0001"),
        json={"instruction": INSTRUCTION, "section_ids": [sections[0]["id"]]},
    )

    assert changed.status_code == 200, changed.text
    after = section_files(client)
    differing = [name for name in before if before[name] != after[name]]
    assert len(differing) == 1 and sorted(after) == sorted(before)
    assert b"Worked example" in after[differing[0]]
    # One change call and one critic call over the changed section only.
    assert [call.split()[0] for call in provider.calls] == ["change"]
    assert provider.reviews == [[sections[0]["id"]]]
    assert lecture_state(client) == ("ready", None, "review_draft")
    latest = client.get(CHANGE, headers=professor_headers()).json()["latest"]
    assert latest["instruction"] == INSTRUCTION.strip()
    assert latest["section_ids"] == [sections[0]["id"]]
    assert (latest["selection"], latest["base"]) == ("professor", "draft")


def test_published_lecture_changes_in_the_background_and_students_keep_the_publication(
    tmp_path, monkeypatch
):
    provider = ScriptedProvider()
    client = drafted_client(tmp_path, monkeypatch, provider)
    publish(client)
    published = section_files(client, published=True)
    assert lecture_state(client) == ("published", None, "none")

    with client:
        accepted = client.post(
            CHANGE,
            headers=change_headers("change-background-0001", background=True),
            json={"instruction": INSTRUCTION},
        )
        assert accepted.status_code == 202, accepted.text
        for _ in range(500):
            state = lecture_state(client)
            if state[0] != "generating":
                break
            time.sleep(0.02)

    assert state == ("ready", None, "review_draft")
    assert provider.calls[0] == "select" and provider.calls.count("select") == 1
    assert [call.split()[0] for call in provider.calls[1:]] == ["change"]
    assert section_files(client, published=True) == published
    draft = section_files(client)
    assert sum(draft[name] != published[name] for name in published) == 1
    latest = client.get(CHANGE, headers=professor_headers()).json()["latest"]
    assert (latest["selection"], latest["base"], latest["reasons"]) == (
        "automatic",
        "published",
        {latest["section_ids"][0]: "Fits."},
    )


def test_generation_states_show_generating_then_the_failure_beside_the_publication(
    tmp_path, monkeypatch
):
    client = drafted_client(tmp_path, monkeypatch, ScriptedProvider())
    publish(client)
    release = asyncio.Event()

    async def generate(*_args, **_kwargs):
        await release.wait()
        raise CanvasChangeRequestError(GOALS_CHANGE_MESSAGE)

    monkeypatch.setattr(
        "lecturepilot.authoring.canvas_change_routes.generate_canvas_change", generate
    )
    with client:
        accepted = client.post(
            CHANGE,
            headers=change_headers("change-states-0001", background=True),
            json={"instruction": INSTRUCTION},
        )
        assert accepted.status_code == 202, accepted.text
        assert lecture_state(client) == ("generating", None, "wait")
        client.portal.call(release.set)
        for _ in range(200):
            state = lecture_state(client)
            if state[0] != "generating":
                break
            time.sleep(0.01)

    assert state == ("published", GOALS_CHANGE_MESSAGE, "none")


def test_rewriting_an_approved_checkpoint_fails_with_the_goals_message(tmp_path, monkeypatch):
    provider = ScriptedProvider(checkpoint=True)
    client = drafted_client(tmp_path, monkeypatch, provider)
    before = section_files(client)

    failed = client.post(
        CHANGE,
        headers=change_headers("change-checkpoint-0001"),
        json={"instruction": "Change the checkpoint question."},
    )

    assert failed.status_code == 409, failed.text
    assert failed.json()["detail"] == GOALS_CHANGE_MESSAGE
    assert section_files(client) == before
    assert lecture_state(client) == ("ready", GOALS_CHANGE_MESSAGE, "review_draft")
