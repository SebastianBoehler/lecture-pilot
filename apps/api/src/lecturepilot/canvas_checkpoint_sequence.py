from lecturepilot.canvas_models import CanvasBlock


def checkpoint_block(block_id: str, caption: str | None, text: str) -> CanvasBlock:
    if not caption or not caption.startswith("[sequence] "):
        return CanvasBlock(id=block_id, type="checkpoint", text=text, caption=caption)
    lines = text.splitlines()
    option_lines = [line for line in lines if line.startswith("- ")]
    question = "\n".join(lines[: -len(option_lines)]).strip() if option_lines else ""
    options = [line[2:].strip() for line in option_lines]
    if (
        not question
        or not 2 <= len(options) <= 5
        or lines[-len(option_lines) :] != option_lines
        or not all(options)
        or len(set(options)) != len(options)
    ):
        raise ValueError("Checkpoint sequence requires a question and 2–5 distinct choices.")
    return CanvasBlock(
        id=block_id,
        type="checkpoint",
        caption=caption.removeprefix("[sequence] "),
        text=question,
        items=options,
    )
