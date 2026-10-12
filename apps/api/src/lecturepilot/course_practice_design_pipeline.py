"""Goals-first production pipeline for offline benchmarks: goals, then bounded teaching."""

from pathlib import Path
from tempfile import TemporaryDirectory

from lecturepilot.course_learning_intent_proposal import propose_learning_intent
from lecturepilot.course_practice_design_planner import (
    PracticeDesignPlanner,
    ReviewedPracticeDesignProposal,
)
from lecturepilot.teaching_design_runtime import run_implementation_repair


class GoalsFirstPracticeDesignPipeline:
    """Runs the same goal proposal and teaching workflow that professors use.

    The proposed goals are not approved here: the benchmark evaluates generated teaching
    for unreviewed goals and never fabricates a professor decision.
    """

    def __init__(self, planner: PracticeDesignPlanner) -> None:
        self.planner = planner

    async def propose(
        self, *, source, source_revision, allowed_source_paths
    ) -> ReviewedPracticeDesignProposal:
        proposal, _ = await propose_learning_intent(
            self.planner,
            source=source,
            source_revision=source_revision,
            allowed_source_paths=allowed_source_paths,
        )
        with TemporaryDirectory(prefix="practice-design-benchmark-") as root:
            return await run_implementation_repair(
                planner=self.planner,
                root=Path(root),
                authorize=lambda: None,
                source=source,
                source_revision=source_revision,
                allowed_source_paths=allowed_source_paths,
                initial=None,
                protected_intent=proposal.intent(source_revision),
                repair_context=None,
            )
