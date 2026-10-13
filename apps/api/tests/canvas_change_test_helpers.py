"""A drafted two-section lecture and a scripted provider for change-request route tests."""

import json
import re

from authoring_test_helpers import drafted_path, install_author, markdown
from auth_helpers import professor_headers
from lecturepilot.learning_design.course_learning_design_models import (
    LearningDesignApprovalInput,
)
from lecturepilot.learning_design.course_learning_design_store import CourseLearningDesignStore
from test_course_canvas_targeted_repair import _course_client
from test_course_canvas_targeted_repair_resilience import headers

COURSE = "targeted-repair"
LECTURE = "lecture-01"
CHANGE = f"/admin/courses/{COURSE}/lectures/{LECTURE}/canvas/change-request"
DRAFT = f"/admin/courses/{COURSE}/lectures/{LECTURE}/canvas/draft"


class ScriptedProvider:
    """Writes sections, answers the selection call and applies changes; records each call."""

    def __init__(self, *, select=None, checkpoint=False):
        self.select, self.checkpoint = select, checkpoint
        self.calls: list[str] = []
        self.reviews: list[list[str]] = []

    def respond(self, messages, info):
        prompt = str(messages[0].parts[-1].content)
        if "Sections of the lecture" in prompt:
            self.calls.append("select")
            chosen = self.select or re.search(r"^- ([\w-]+):", prompt, re.M).group(1)
            return markdown(json.dumps({"sections": [{"section_id": chosen, "reason": "Fits."}]}))
        path = drafted_path(messages)
        if "Professor change request:" not in prompt:
            self.calls.append("write " + path)
            return markdown(_section(path))
        self.calls.append("change " + path)
        draft = prompt.split("Current draft:\n", 1)[1].split("\nProfessor change request:", 1)[0]
        addition = (
            '<!-- block id="practice-rewritten" type="checkpoint" -->\n'
            ":::checkpoint Apply it\nCompute the score without the transpose.\n:::\n"
            if self.checkpoint
            else '<!-- block id="worked-example" type="paragraph" -->\n'
            "Worked example: the inner product of matching weight and input vectors.\n"
        )
        return markdown(draft.rstrip() + "\n\n" + addition)

    async def complete_review(self, *, candidate_document, **kwargs):
        self.reviews.append([section.id for section in candidate_document.sections])
        return {"issues": []}


def _section(path):
    topic = path.removeprefix("/draft/").removesuffix(".md")
    return (
        f"# {topic}\n\n"
        f'<!-- block id="{topic}-explanation" type="paragraph" -->\n'
        "The score is the inner product of the transposed weight vector and the input.\n\n"
        f'<!-- block id="{topic}-check" type="checkpoint" -->\n'
        ":::checkpoint Apply it\nWhy must the weight and input dimensions match?\n:::\n"
    )


def drafted_client(tmp_path, monkeypatch, provider):
    client = _course_client(tmp_path)
    install_author(client, monkeypatch, provider.respond, provider)
    drafted = client.post(DRAFT, headers=headers("change-initial-draft-0001"))
    assert drafted.status_code == 200, drafted.text
    provider.calls.clear()
    provider.reviews.clear()
    return client


def publish(client):
    layout = client.app.state.canvas_workspace.layout
    store = CourseLearningDesignStore(layout)
    review = store.read(course_id=COURSE, lecture_id=LECTURE)
    store.approve(
        course_id=COURSE,
        lecture_id=LECTURE,
        approval=LearningDesignApprovalInput(
            draft_digest=review.draft_digest,
            source_revision=review.source_revision,
            practice_design_revision=review.practice_design_revision,
            learning_map_revision=review.learning_map.revision,
        ),
        approved_by="professor",
    )
    client.app.state.canvas_workspace.publish_course_canvas_draft(
        course_id=COURSE, lecture_id=LECTURE, published_by="professor"
    )


def section_files(client, *, published=False):
    layout = client.app.state.canvas_workspace.layout
    root = (
        layout.course_canvas_dir(COURSE, LECTURE)
        if published
        else layout.course_canvas_draft_dir(COURSE, LECTURE)
    )
    return {path.name: path.read_bytes() for path in sorted((root / "sections").glob("*.md"))}


def lecture_state(client) -> tuple:
    response = client.get(f"/admin/courses/{COURSE}/lecture-states", headers=professor_headers())
    assert response.status_code == 200, response.text
    item = response.json()["lectures"][0]
    return item["draft"], item["draft_error"], item["next_action"]


def change_headers(key, *, background=False):
    return {**headers(key), **({"Prefer": "respond-async"} if background else {})}
