from lecturepilot import course_canvas_generation_jobs
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.storage_layout import StorageLayout


def test_stale_running_job_is_reclaimed_after_worker_disappears(tmp_path) -> None:
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=0)
    first, first_owner = store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-0001",
    )

    reclaimed, reclaimed_owner = store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-0001",
    )

    assert first_owner is True
    assert reclaimed_owner is True
    assert reclaimed.generation_id == first.generation_id
    assert reclaimed.attempt == 2


def test_generation_key_is_scoped_to_authenticated_actor(tmp_path) -> None:
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=30)
    store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-0001",
    )

    other_actor = store.read(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-2",
        request_key="request-key-0001",
    )

    assert other_actor is None


def test_generation_record_replace_fsyncs_its_parent(tmp_path, monkeypatch) -> None:
    synced: list[object] = []
    monkeypatch.setattr(
        course_canvas_generation_jobs,
        "fsync_directory",
        lambda path: synced.append(path),
    )
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=30)

    store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-durable-0001",
    )

    assert synced == [
        store.layout.course_root("course-1") / "builder" / "generations" / "lecture-01"
    ]


def test_generation_store_durably_creates_its_private_directory(tmp_path, monkeypatch) -> None:
    ensured: list[object] = []

    def ensure(path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        ensured.append(path)

    monkeypatch.setattr(
        course_canvas_generation_jobs,
        "ensure_durable_directory",
        ensure,
    )
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=30)

    store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-durable-directory-0001",
    )

    assert ensured == [
        store.layout.course_root("course-1") / "builder" / "generations" / "lecture-01"
    ]


def test_generation_records_prune_old_terminal_jobs_but_keep_running(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        course_canvas_generation_jobs,
        "MAX_TERMINAL_GENERATION_RECORDS",
        3,
    )
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=30)
    running, _ = store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-running-0001",
    )
    terminal_ids: list[str] = []
    for index in range(5):
        request_key = f"request-key-terminal-{index:04d}"
        job, _ = store.begin(
            course_id="course-1",
            lecture_id="lecture-01",
            actor_user_id="professor-1",
            request_key=request_key,
        )
        terminal_ids.append(job.generation_id)
        store.fail(
            job,
            actor_user_id="professor-1",
            request_key=request_key,
            error_code="test_failure",
        )

    directory = store.layout.course_root("course-1") / "builder" / "generations" / "lecture-01"
    records = [
        course_canvas_generation_jobs.CanvasGenerationJob.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        for path in directory.glob("*.json")
    ]

    assert {job.generation_id for job in records if job.status == "running"} == {
        running.generation_id
    }
    assert {job.generation_id for job in records if job.status == "failed"} == set(
        terminal_ids[-3:]
    )
    assert [path.name for path in directory.glob("*.lock")] == [".generation.lock"]
