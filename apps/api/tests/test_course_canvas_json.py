from __future__ import annotations

import pytest

from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.model_client import ModelExecutionError


def test_parse_model_json_accepts_fenced_json() -> None:
    payload = parse_model_json('```json\n{"title": "Draft", "sections": []}\n```')

    assert payload["title"] == "Draft"


def test_parse_model_json_rejects_provider_text_wrapping() -> None:
    with pytest.raises(ModelExecutionError):
        parse_model_json('Here is the draft:\n{"title": "Draft", "sections": []}\nDone.')


def test_parse_model_json_repairs_latex_backslashes() -> None:
    payload = parse_model_json(r'{"title": "Draft", "formula": "P(C \mid x)=\alpha"}')

    assert payload["formula"] == r"P(C \mid x)=\alpha"


def test_parse_model_json_rejects_missing_object() -> None:
    with pytest.raises(ModelExecutionError):
        parse_model_json("not json")


def test_parse_model_json_classifies_empty_output_as_model_failure() -> None:
    with pytest.raises(ModelExecutionError, match="empty response"):
        parse_model_json(None)
