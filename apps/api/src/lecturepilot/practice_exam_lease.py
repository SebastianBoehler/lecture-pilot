"""Renew an owned exam attempt while its bounded provider job is running."""

import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def practice_exam_lease(store, job, *, user_id, request_key):
    async def renew():
        while True:
            await asyncio.sleep(max(0.01, store.lease.total_seconds() / 3))
            await asyncio.to_thread(store.renew, job, user_id=user_id, request_key=request_key)

    try:
        async with asyncio.TaskGroup() as group:
            renewal = group.create_task(renew())
            try:
                yield
                await asyncio.to_thread(store.renew, job, user_id=user_id, request_key=request_key)
            finally:
                renewal.cancel()
    except BaseExceptionGroup as exc:
        if len(exc.exceptions) == 1:
            raise exc.exceptions[0] from exc
        raise
