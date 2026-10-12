"""One process-wide bound on concurrent background generation jobs.

Canvas drafts (goal-to-teaching-to-canvas authoring and repairs) and practice exams run as
asyncio tasks inside the API process. On a small VM their provider fan-out, source parsing
and memory use must not grow with the number of professors or students starting jobs, so
every kind shares the same FIFO slots. Extra jobs wait for a slot instead of failing; their
durable leases keep renewing while they wait, so their status stays "running".
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

BACKGROUND_GENERATION_SLOTS = 2


@asynccontextmanager
async def background_generation_slot(app: Any) -> AsyncIterator[None]:
    slots = getattr(app.state, "background_generation_slots", None)
    if slots is None:
        slots = app.state.background_generation_slots = asyncio.Semaphore(
            BACKGROUND_GENERATION_SLOTS
        )
    async with slots:
        yield
