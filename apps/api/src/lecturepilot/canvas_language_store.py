from lecturepilot.canvas_language_variants import LanguageVariant, validate_variant
from lecturepilot.course_canvas_context import read_current_published_snapshot
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.storage_layout import safe_id


class CanvasLanguageStore:
    def __init__(self, layout):
        self.layout = layout

    def snapshot(self, course_id, lecture_id):
        snapshot = read_current_published_snapshot(
            self.layout.course_canvas_dir(course_id, lecture_id),
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise ValueError("Publish the canonical canvas before preparing another language.")
        return snapshot

    def path(self, course_id, lecture_id, language, *, published=False):
        if language not in {"de", "en"}:
            raise ValueError("Unsupported teaching language.")
        return (
            self.layout.course_root(course_id)
            / "builder"
            / "language-variants"
            / safe_id(lecture_id)
            / language
            / ("published.json" if published else "draft.json")
        )

    def read(self, course_id, lecture_id, language, *, published=False, snapshot=None):
        path = self.path(course_id, lecture_id, language, published=published)
        if not path.exists():
            return None
        variant = LanguageVariant.model_validate_json(path.read_text())
        if variant.language != language or (published and not variant.published_at):
            raise ValueError("Language publication metadata is invalid.")
        validate_variant(variant, snapshot or self.snapshot(course_id, lecture_id))
        return variant

    def write(self, course_id, lecture_id, variant, *, published=False):
        validate_variant(variant, self.snapshot(course_id, lecture_id))
        atomic_write_json(
            self.path(course_id, lecture_id, variant.language, published=published),
            variant.model_dump(mode="json"),
        )

    def assessment_language(self, course_id, lecture_id, snapshot):
        import json
        from lecturepilot.canvas_language_variants import binding

        path = self.path(course_id, lecture_id, "en").parent.parent / "assessment-language.json"
        if not path.exists():
            return None
        record = json.loads(path.read_text())
        if record.get("publication_binding") != binding(snapshot):
            return None
        if record.get("language") not in {"de", "en"}:
            raise ValueError("Recorded assessment language is invalid.")
        return record["language"]

    def declare_assessment_language(self, course_id, lecture_id, snapshot, language, user_id):
        from lecturepilot.canvas_language_variants import binding

        current = self.assessment_language(course_id, lecture_id, snapshot)
        if current is not None and current != language:
            raise ValueError("The recorded assessment language differs for this publication.")
        path = self.path(course_id, lecture_id, "en").parent.parent / "assessment-language.json"
        atomic_write_json(
            path,
            {
                "publication_binding": binding(snapshot),
                "language": language,
                "reviewed_by": user_id,
            },
        )
