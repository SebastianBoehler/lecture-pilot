from authoring_test_helpers import install_author, markdown
from lecturepilot.llm.model_client import ModelExecutionError
from test_course_canvas_targeted_repair import _course_client
from test_course_canvas_targeted_repair_resilience import Reviewer, headers

SECTION = (
    '# Inner product\n<!-- block id="explain" type="paragraph" -->\n'
    "The weight and input vectors must have matching dimensions for the inner product.\n\n"
    '<!-- block id="check" type="checkpoint" -->\n'
    ":::checkpoint Apply it\nExplain why the vector dimensions must match.\n:::\n"
)


def test_fresh_agent_failure_and_failed_retry_keep_one_durable_session(tmp_path, monkeypatch):
    client = _course_client(tmp_path)
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"

    def interrupted(messages, info):
        raise ModelExecutionError("Provider connection interrupted")

    install_author(client, monkeypatch, interrupted, Reviewer())
    first = client.post(path, headers=headers("native-failure-0001"))
    assert first.status_code == 502, first.text
    assert first.headers.get("X-Generation-Repairable") == "true"
    restored = client.get(path, headers=headers("native-failure-0001"))
    assert restored.status_code == 404
    assert restored.headers.get("X-Generation-Repairable") == "true"
    retry = client.post(path + "/repair", headers=headers("native-failure-0002"))
    assert retry.status_code == 502, retry.text
    assert retry.headers.get("X-Generation-Repairable") == "true"

    install_author(client, monkeypatch, lambda messages, info: markdown(SECTION), Reviewer())
    result = client.post(path + "/repair", headers=headers("native-success-0003"))
    assert result.status_code == 200, result.text
    status = client.get(path + "/status", headers=headers("native-success-0003"))
    assert status.json()["authoring_metrics"]["resumes"] == 2
