from pathlib import Path

import pytest

from lecturepilot.canvas_component_blocks import read_component_block


def test_component_without_authored_title_uses_readable_id(tmp_path: Path) -> None:
    components_dir = tmp_path / "components"
    components_dir.mkdir()
    (components_dir / "llm-history-process.yaml").write_text(
        """id: llm-history-process
version: 1
type: process_explorer
prompt: Explore the progression of language models.
data:
  steps:
    - title: Early language models
      text: Begin with statistical models.
    - title: Large language models
      text: Continue with neural models at scale.
""",
        encoding="utf-8",
    )

    block = read_component_block(
        "llm-history",
        "llm-history-process.yaml",
        "",
        components_dir=components_dir,
    )

    assert block.caption == "LLM history"
    assert block.caption != block.component_ref


@pytest.mark.parametrize(
    "body",
    [
        '{"id": "inline", "version": 1}',
        '{"type": "single_choice_quiz", "version": 1}',
        '{"id": "inline", "type": "single_choice_quiz"}',
        '{"id": "inline", "type": "single_choice_quiz", "version": true}',
    ],
)
def test_inline_component_requires_complete_strict_identity(body: str) -> None:
    with pytest.raises(ValueError, match="complete id, type, and integer version"):
        read_component_block("inline-block", None, body)
