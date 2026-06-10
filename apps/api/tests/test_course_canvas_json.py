from __future__ import annotations

import pytest

from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.providers import ProviderConfigurationError


def test_parse_model_json_accepts_fenced_json() -> None:
    payload = parse_model_json('```json\n{"title": "Draft", "sections": []}\n```')

    assert payload["title"] == "Draft"


def test_parse_model_json_extracts_json_from_provider_text() -> None:
    payload = parse_model_json('Here is the draft:\n{"title": "Draft", "sections": []}\nDone.')

    assert payload["sections"] == []


def test_parse_model_json_repairs_latex_backslashes() -> None:
    payload = parse_model_json(r'{"title": "Draft", "formula": "P(C \mid x)=\alpha"}')

    assert payload["formula"] == r"P(C \mid x)=\alpha"


def test_parse_model_json_rejects_missing_object() -> None:
    with pytest.raises(ProviderConfigurationError):
        parse_model_json("not json")
