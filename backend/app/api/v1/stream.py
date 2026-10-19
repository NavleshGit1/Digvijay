import asyncio
import json
from collections.abc import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.locks import redis_client

router = APIRouter(tags=["Stream"])


async def event_generator() -> AsyncGenerator[str, None]:
    """Streams live Server-Sent Events (SSE) from Redis pub/sub to frontend."""
    # Yield initial connection handshake
    yield f"event: connected\ndata: {json.dumps({'message': 'SSE stream established'})}\n\n"

    try:
        pubsub = redis_client.pubsub()
        pubsub.subscribe("jobs:progress", "alerts:new")

        while True:
            # Non-blocking poll
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                channel = message.get("channel", "update")
                data = message.get("data", "{}")
                yield f"event: {channel}\ndata: {data}\n\n"
            else:
                # Keepalive heartbeat
                yield ": keepalive\n\n"
                await asyncio.sleep(2.0)
    except Exception:
        # Fallback heartbeat stream if Redis is unreachable
        while True:
            yield ": keepalive\n\n"
            await asyncio.sleep(3.0)


@router.get("/stream")
async def sse_stream() -> StreamingResponse:
    """Server-Sent Events endpoint streaming job progress, alerts, and system heartbeats."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
