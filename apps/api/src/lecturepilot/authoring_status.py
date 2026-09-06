from lecturepilot.authoring_models import AuthoringMetrics
from lecturepilot.storage_layout import safe_id


def authoring_metrics_path(layout, course_id, lecture_id, generation_id):
    return (
        layout.course_root(course_id)
        / "builder"
        / "authoring-metrics"
        / safe_id(lecture_id)
        / f"{safe_id(generation_id)}.json"
    )


def read_authoring_metrics(layout, job):
    path = authoring_metrics_path(layout, job.course_id, job.lecture_id, job.generation_id)
    return AuthoringMetrics.model_validate_json(path.read_text()) if path.exists() else None
