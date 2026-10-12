from __future__ import annotations

from fastapi import FastAPI

from lecturepilot.analytics.analytics import AnalyticsStore
from lecturepilot.learner.learner_state import LearnerStateStore
from lecturepilot.core.observability import Observability
from lecturepilot.learner.user_memory import UserMemoryStore


def user_memory_store(app: FastAPI) -> UserMemoryStore:
    store = app.state.user_memory_store
    layout = getattr(app.state.canvas_workspace, "layout", None)
    if layout is not None and store.layout is not layout:
        store = UserMemoryStore(layout)
        app.state.user_memory_store = store
    return store


def learner_state_store(app: FastAPI) -> LearnerStateStore:
    store = app.state.learner_state
    layout = getattr(app.state.canvas_workspace, "layout", None)
    if layout is not None and store.layout is not layout:
        store = LearnerStateStore(layout)
        app.state.learner_state = store
    return store


def analytics_store(app: FastAPI) -> AnalyticsStore:
    return app.state.analytics_store


def observability(app: FastAPI) -> Observability:
    return getattr(app.state, "observability", Observability())
