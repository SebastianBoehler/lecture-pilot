"""A four-goal, five-section lecture with a scripted provider for authoring call budgets."""

from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_job import AuthoringJob
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.models import ProviderSettings
from authoring_test_helpers import drafted_path, is_repair, markdown
from practice_design_test_helpers import proposal, target

SECTION_COUNT = 5
GOAL_COUNT = 4


def facts():
    return [
        f"Topic {n} states that evidence item {n} justifies claim {n} by a stated rule."
        for n in range(1, SECTION_COUNT + 1)
    ]


def lecture_source():
    return CanvasDocument(
        id="lecture-01",
        course_id="course-a",
        lecture_id="lecture-01",
        title="Evidence",
        source_kind="markdown",
        source_ref="lecture.md",
        workspace_path="source/lecture.md",
        sections=[
            CanvasSection(
                id=f"topic-{n}",
                title=f"Topic {n}",
                source_ref="lecture.md",
                blocks=[CanvasBlock(id=f"fact-{n}", type="paragraph", text=fact)],
            )
            for n, fact in enumerate(facts(), 1)
        ],
    )


def goal_target(n, *, task_suffix=""):
    return target(
        id=f"goal-{n}",
        baseline_task=f"Justify claim {n} from evidence item {n}.{task_suffix}",
        independent_exit_task=f"Justify a parallel claim {n} from new evidence.",
        delayed_transfer_task=f"Justify claim {n} after the surface details change.",
        source_refs=("lecture.md",),
        source_excerpt=facts()[n - 1],
    )


def lecture_design(*, changed_goal=None):
    source = lecture_source()
    targets = tuple(
        goal_target(n, task_suffix=" Name the rule." if n == changed_goal else "")
        for n in range(1, GOAL_COUNT + 1)
    )
    return PracticeDesign.create(
        course_id=source.course_id,
        lecture_id=source.lecture_id,
        lecture_title=source.title,
        objective="Justify each claim from its cited evidence.",
        planning_context=proposal().planning_context,
        source_revision="a" * 64,
        targets=targets,
    )


class ScriptedCritic:
    """Returns scripted issues per review call and records the reviewed section ids."""

    def __init__(self, *scripts):
        self.scripts, self.reviewed = list(scripts), []

    async def complete_review(self, *, candidate_document, checkpoints, **kwargs):
        self.reviewed.append([section.id for section in candidate_document.sections])
        script = self.scripts.pop(0) if self.scripts else (lambda document, checkpoints: [])
        return {"issues": script(candidate_document, checkpoints)}


def lecture_job(root, critic, *, design=None, **changes):
    source = lecture_source()
    return AuthoringJob(
        root=root,
        source=source,
        design=design or lecture_design(),
        source_revision="a" * 64,
        settings=ProviderSettings(
            provider="openai", model="openai/test", api_key_env="OPENAI_API_KEY", capabilities=set()
        ),
        reviewer=CanvasQualityReviewer(critic),
        **changes,
    )


class ScriptedAuthor:
    """Writes one valid Markdown body per section call and counts writes and repairs."""

    def __init__(self):
        self.writes, self.repairs = [], []

    def respond(self, messages, info):
        path = drafted_path(messages)
        (self.repairs if is_repair(messages) else self.writes).append(path)
        topic = path.removeprefix("/draft/").removesuffix(".md")
        return markdown(
            f"# {topic}\n\n"
            f'<!-- block id="{topic}-explanation" type="paragraph" -->\n'
            f"The {topic} evidence justifies its claim by the stated rule.\n\n"
            f'<!-- block id="{topic}-check" type="checkpoint" -->\n'
            f":::checkpoint Apply it\nWhy does the {topic} evidence justify its claim?\n:::\n"
        )

    def model(self):
        return FunctionModel(self.respond)
