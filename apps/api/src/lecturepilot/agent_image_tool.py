from __future__ import annotations

from typing import Any

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.generated_infographics import _safe_slug
from lecturepilot.image_generation import ImageGenerationError
from lecturepilot.storage_layout import safe_id


class AgentImageToolError(RuntimeError):
    """Raised when the tutor cannot generate a learner image asset."""


def generate_workspace_image(
    *,
    image_generator: Any | None,
    layout: Any,
    user_id: str,
    course_id: str,
    lecture_id: str,
    prompt: str,
    section_id: str,
    filename: str | None,
) -> dict[str, str]:
    if image_generator is None:
        raise AgentImageToolError("No image provider is configured.")
    section = CanvasSection(
        id=safe_id(section_id),
        title="Generated infographic",
        source_ref="student workspace",
        blocks=[CanvasBlock(id="prompt", type="paragraph", text=prompt)],
    )
    try:
        generated = image_generator.generate_infographic(prompt=prompt, section=section)
        if generated.extension == "svg":
            raise ImageGenerationError("Image providers must return raster images.")
    except ImageGenerationError as exc:
        raise AgentImageToolError(str(exc)) from exc
    output_name = f"{_safe_slug(filename or section.id)}.{generated.extension}"
    asset_dir = layout.user_canvas_dir(user_id, course_id, lecture_id) / "student-assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / output_name).write_bytes(generated.content)
    student_key = layout.user_key(user_id)
    asset_url = (
        f"/workspace-assets/{safe_id(course_id)}/{safe_id(lecture_id)}/"
        f"{student_key}/student-assets/{output_name}"
    )
    markdown_caption = generated.caption.replace("[", "(").replace("]", ")")
    return {
        "path": f"/lecture/canvas/student-assets/{output_name}",
        "asset_url": asset_url,
        "caption": generated.caption,
        "markdown": f"![{markdown_caption}]({asset_url})",
    }
