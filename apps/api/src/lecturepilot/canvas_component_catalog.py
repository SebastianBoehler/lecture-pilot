from __future__ import annotations

from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasBlock, CanvasComponentData
from lecturepilot.model_generated_ids import safe_generated_id, trim_generated_text


SUPPORTED_COMPONENT_TYPES = (
    "single_choice_quiz",
    "interactive_chart",
    "process_explorer",
    "visual_artifact",
    "mechanism_comparison",
)


def component_catalog_instruction() -> str:
    return (
        "Use a component only when interacting with it improves understanding beyond reading. "
        "Choose the smallest visual grammar that exposes the teaching mechanism: do not add "
        "decorative metrics, controls, panels, or alternate views. Keep important comparisons "
        "simultaneously visible, use shared scales, label quantities and units, and state the "
        "causal takeaway next to the marks it explains. "
        "Supported component_type values are: single_choice_quiz for one checked answer; "
        "interactive_chart for exact source-supported numeric comparisons or parameter changes; "
        "process_explorer for one ordered mechanism or algorithm; and visual_artifact for a "
        "composable data-only visual using a flow, timeline, grid, or plot layout; and "
        "mechanism_comparison when two to four approaches must stay visible together. "
        "Every component needs component_id, component_type, component_version=1, caption, prompt "
        "text, and component_data. For interactive_chart, component_data must contain chart_type "
        "(bar, line, scatter, or heatmap), x_label, y_label, control_label, control_type, and one "
        "or more frames with a label and explanation. Use control_type=buttons for a small set of "
        "categorical states such as raw versus learned features. Use control_type=slider for an "
        "ordered numeric parameter such as a threshold or cost. Bar and line charts use labels "
        "plus one numeric value per label in every frame. Scatter charts use at least two labeled "
        "x/y points per frame. "
        "Heatmaps use column labels, row_labels, and a rectangular numeric matrix per frame. "
        "Use empty arrays for unused values, points, matrix, row_labels, and steps. "
        "For process_explorer, component_data must contain at least two title/text steps and empty "
        "chart arrays. For visual_artifact, choose visual_layout flow, timeline, grid, or plot and "
        "compose only the needed visual_nodes, visual_edges, visual_series, and visual_annotations. "
        "Flow and timeline show relationships between referenced node ids; grid keeps concepts or "
        "alternatives simultaneously visible; plot uses labeled axes and line, bar, or point series. "
        "Keep unused visual arrays empty and visual_layout=null for other component types. "
        "For mechanism_comparison, provide two to four frames with the same outcome labels and "
        "exactly one value per label. Show every approach simultaneously without a frame control. "
        "For single_choice_quiz, use items for the answer text, "
        "option_ids for stable answer ids, answer_index for the one correct answer, and empty "
        "component_data arrays. Use component_data=null for non-component blocks. Never output "
        "code, JSX, HTML, scripts, URLs, or arbitrary React components."
    )


def component_block_from_payload(raw_block: dict, block_id: str) -> CanvasBlock:
    component_type = str(
        raw_block.get("component_type") or raw_block.get("kind") or "single_choice_quiz"
    )[:120]
    component_id = safe_generated_id(str(raw_block.get("component_id") or block_id))
    items, option_ids, answer_index = _component_options(raw_block)
    data = component_data_from_payload(raw_block.get("component_data", raw_block.get("data")))
    return CanvasBlock(
        id=block_id,
        type="component",
        text=trim_generated_text(str(raw_block.get("text") or raw_block.get("prompt") or ""), 1200)
        or None,
        items=items,
        caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        answer_index=answer_index,
        component_id=component_id,
        component_type=component_type,
        component_ref=_component_ref(block_id),
        component_version=_component_version(
            raw_block.get("component_version", raw_block.get("version"))
        ),
        option_ids=option_ids,
        component_data=data,
    )


def component_data_from_payload(value: object) -> CanvasComponentData | None:
    if not isinstance(value, dict):
        return None
    try:
        return CanvasComponentData.model_validate(value)
    except ValidationError:
        return None


def component_spec_issue(block: CanvasBlock) -> str | None:
    component_type = block.component_type or "unknown"
    if component_type not in SUPPORTED_COMPONENT_TYPES:
        return f"uses unsupported component_type {component_type}."
    if component_type == "single_choice_quiz":
        if len(block.items) < 2 or block.answer_index is None:
            return "needs at least two options and one explicit correct answer."
        return None
    data = block.component_data
    if data is None:
        return "needs valid component_data."
    if component_type == "interactive_chart":
        return _chart_spec_issue(data)
    if component_type == "visual_artifact":
        if block.component_version != 1:
            return "uses unsupported visual_artifact component_version."
        return _visual_artifact_issue(data)
    if component_type == "mechanism_comparison":
        return _mechanism_comparison_issue(data)
    if len(data.steps) < 2:
        return "needs at least two ordered steps."
    return None


def _visual_artifact_issue(data: CanvasComponentData) -> str | None:
    if data.visual_layout is None:
        return "needs a flow, timeline, grid, or plot visual_layout."
    node_ids = [node.id for node in data.visual_nodes]
    if len(set(node_ids)) != len(node_ids):
        return "needs unique visual node ids."
    referenced_ids = {
        node_id for edge in data.visual_edges for node_id in (edge.from_id, edge.to_id)
    } | {
        annotation.target_id
        for annotation in data.visual_annotations
        if annotation.target_id is not None
    }
    if not referenced_ids.issubset(node_ids):
        return "references an unknown visual node."
    if any(edge.from_id == edge.to_id for edge in data.visual_edges):
        return "cannot connect a visual node to itself."
    if data.visual_layout == "plot":
        if not data.x_label or not data.y_label:
            return "needs labeled axes for a visual plot."
        if not data.visual_series or any(len(series.points) < 2 for series in data.visual_series):
            return "needs at least two finite points in every visual series."
        if data.visual_nodes or data.visual_edges:
            return "uses series and annotations instead of nodes in a visual plot."
        return None
    if data.visual_series:
        return "uses visual series only with the plot layout."
    if len(data.visual_nodes) < 2:
        return "needs at least two visual nodes."
    if data.visual_layout == "grid" and data.visual_edges:
        return "uses visual edges only with flow or timeline layouts."
    return None


def _mechanism_comparison_issue(data: CanvasComponentData) -> str | None:
    if not 2 <= len(data.frames) <= 4:
        return "needs two to four mechanism frames."
    if len(data.labels) < 2:
        return "needs at least two shared outcome labels."
    if any(len(frame.values) != len(data.labels) for frame in data.frames):
        return "needs exactly one outcome value per label in every mechanism frame."
    has_profiles = any(frame.points for frame in data.frames)
    if has_profiles and (
        not data.x_label or not data.y_label or any(len(frame.points) < 2 for frame in data.frames)
    ):
        return "needs labeled axes and at least two profile points in every mechanism frame."
    if data.control_type is not None:
        return "shows every mechanism simultaneously and cannot use a frame control."
    return None


def _chart_spec_issue(data: CanvasComponentData) -> str | None:
    if data.chart_type is None or not data.frames:
        return "needs chart_type and at least one frame."
    if len(data.frames) > 1 and not data.control_label:
        return "needs control_label when more than one frame is provided."
    if data.chart_type in {"bar", "line"}:
        if len(data.labels) < 2:
            return "needs at least two labels."
        if any(len(frame.values) != len(data.labels) for frame in data.frames):
            return "needs exactly one numeric value per label in every frame."
        return None
    if data.chart_type == "scatter":
        if not data.x_label or not data.y_label:
            return "needs x_label and y_label for scatter axes."
        if any(len(frame.points) < 2 for frame in data.frames):
            return "needs at least two labeled points in every scatter frame."
        return None
    if not 2 <= len(data.labels) <= 12 or len(data.row_labels) < 2:
        return "needs 2 to 12 column labels and at least two row_labels for a heatmap."
    if any(
        len(frame.matrix) != len(data.row_labels)
        or any(len(row) != len(data.labels) for row in frame.matrix)
        for frame in data.frames
    ):
        return "needs a rectangular matrix matching row_labels and labels in every frame."
    return None


def _component_options(raw_block: dict) -> tuple[list[str], list[str], int | None]:
    value = raw_block.get("options")
    if not isinstance(value, list):
        return _schema_component_options(raw_block)
    items: list[str] = []
    option_ids: list[str] = []
    answer_index = None
    for option in value[:8]:
        if not isinstance(option, dict):
            continue
        text = trim_generated_text(str(option.get("text") or option.get("label") or ""), 240)
        if not text:
            continue
        if option.get("correct") is True:
            answer_index = len(items)
        option_ids.append(safe_generated_id(str(option.get("id") or chr(65 + len(items)))))
        items.append(text)
    return items, option_ids, answer_index


def _schema_component_options(raw_block: dict) -> tuple[list[str], list[str], int | None]:
    raw_items = raw_block.get("items")
    if not isinstance(raw_items, list):
        return [], [], None
    items = [text for item in raw_items[:8] if (text := trim_generated_text(str(item), 240))]
    raw_ids = raw_block.get("option_ids")
    option_ids = [
        safe_generated_id(
            str(
                raw_ids[index]
                if isinstance(raw_ids, list) and index < len(raw_ids)
                else chr(65 + index)
            )
        )
        for index in range(len(items))
    ]
    answer_index = raw_block.get("answer_index")
    if not isinstance(answer_index, int) or not 0 <= answer_index < len(items):
        answer_index = None
    return items, option_ids, answer_index


def _component_ref(block_id: str) -> str:
    return f"{safe_generated_id(block_id)}.yaml"


def _component_version(value: object) -> int:
    if isinstance(value, int) and value >= 1:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) >= 1:
        return int(value)
    return 1
