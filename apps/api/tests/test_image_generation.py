import base64

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.image_generation_gemini import GeminiImageGenerator
from lecturepilot.image_generation_huggingface import HuggingFaceImageGenerator
from lecturepilot.image_generation_openrouter import OpenRouterImageGenerator
from lecturepilot.image_generation_registry import image_generator_from_env


def test_gemini_image_generator_posts_native_image_request(monkeypatch) -> None:
    captured = {}

    def fake_post_json(
        *, url: str, headers: dict[str, str], payload: dict, timeout_seconds: int
    ) -> dict:
        captured.update(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": base64.b64encode(b"png-bytes").decode("ascii"),
                                }
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr("lecturepilot.image_generation_gemini.post_json", fake_post_json)
    generator = GeminiImageGenerator(
        api_key="gemini-key",
        model="gemini-3.1-flash-image",
        aspect_ratio="16:9",
        image_size="1K",
        timeout_seconds=12,
    )
    section = CanvasSection(
        id="student-bayes-flow",
        title="Bayes flow",
        blocks=[
            CanvasBlock(
                id="student-bayes-flow-list",
                type="list",
                items=["Prior", "Likelihood", "Posterior", "Decision"],
            )
        ],
    )

    result = generator.generate_infographic(prompt="Create an infographic.", section=section)

    assert result.content == b"png-bytes"
    assert result.extension == "png"
    assert result.model == "gemini-3.1-flash-image"
    assert captured["url"].endswith("/v1/models/gemini-3.1-flash-image:generateContent")
    assert captured["timeout_seconds"] == 12
    assert "generationConfig" not in captured["payload"]
    assert captured["headers"]["x-goog-api-key"] == "gemini-key"
    prompt = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "Bayes flow" in prompt
    assert "Prior" in prompt
    assert "16:9" in prompt


def test_openrouter_image_generator_reads_data_url(monkeypatch) -> None:
    def fake_post_json(*, url: str, headers: dict[str, str], payload: dict, timeout_seconds: int):
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert headers["Authorization"] == "Bearer openrouter-key"
        assert payload["modalities"] == ["image", "text"]
        data_url = "data:image/png;base64," + base64.b64encode(b"router-png").decode("ascii")
        return {"choices": [{"message": {"images": [{"image_url": {"url": data_url}}]}}]}

    monkeypatch.setattr("lecturepilot.image_generation_openrouter.post_json", fake_post_json)
    result = OpenRouterImageGenerator(api_key="openrouter-key").generate_infographic(
        prompt="Create an infographic.",
        section=_section(),
    )

    assert result.content == b"router-png"
    assert result.extension == "png"
    assert result.provider == "openrouter"


def test_huggingface_image_generator_reads_raw_bytes(monkeypatch) -> None:
    captured = {}

    def fake_post_image_bytes(
        *, url: str, headers: dict[str, str], payload: dict, timeout_seconds: int
    ):
        captured.update({"url": url, "headers": headers, "payload": payload})
        return b"hf-image", "image/webp"

    monkeypatch.setattr(
        "lecturepilot.image_generation_huggingface.post_image_bytes",
        fake_post_image_bytes,
    )
    result = HuggingFaceImageGenerator(
        api_key="hf-key",
        model="black-forest-labs/FLUX.1-dev",
    ).generate_infographic(prompt="Create an infographic.", section=_section())

    assert result.content == b"hf-image"
    assert result.extension == "webp"
    assert result.provider == "huggingface"
    assert captured["url"].endswith("/black-forest-labs/FLUX.1-dev")
    assert captured["headers"]["Authorization"] == "Bearer hf-key"
    assert captured["payload"]["inputs"]


def test_image_generator_registry_prefers_gemini(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_IMAGE_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)

    generator = image_generator_from_env()

    assert isinstance(generator, GeminiImageGenerator)


def test_image_generator_registry_can_force_huggingface(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_IMAGE_PROVIDER", "huggingface")
    monkeypatch.setenv("HF_TOKEN", "hf-key")

    generator = image_generator_from_env()

    assert isinstance(generator, HuggingFaceImageGenerator)


def _section() -> CanvasSection:
    return CanvasSection(
        id="student-bayes-flow",
        title="Bayes flow",
        blocks=[
            CanvasBlock(
                id="student-bayes-flow-list",
                type="list",
                items=["Prior", "Likelihood", "Posterior", "Decision"],
            )
        ],
    )
