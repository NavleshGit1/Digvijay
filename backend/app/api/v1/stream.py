import asyncio
import json
from collections.abc import AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
import structlog

from app.core.locks import redis_client
from app.services.clock import get_clock

logger = structlog.get_logger()
router = APIRouter(tags=["Stream"])


async def event_generator() -> AsyncGenerator[str, None]:
    """Streams live Server-Sent Events (SSE) from Redis pub/sub to frontend."""
    # Yield initial connection handshake
    yield f"event: connected\ndata: {json.dumps({'message': 'SSE stream established'})}\n\n"

    try:
        pubsub = redis_client.pubsub()
        pubsub.subscribe("jobs:progress", "alerts:new", "events:ingested", "telemetry:update")

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
    except Exception as exc:
        logger.warning("SSE: Redis pubsub unreachable, yielding heartbeat", exc_info=exc)
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


@router.get("/ws/info")
async def websocket_info() -> JSONResponse:
    """Returns metadata about the WebSocket endpoint and available channels."""
    return JSONResponse({
        "status": "active",
        "protocol": "airops-nexus-ws-v1",
        "endpoints": ["/api/v1/ws", "/ws"],
        "channels": ["jobs:progress", "alerts:new", "events:ingested", "telemetry:update"],
        "capabilities": ["duplex_messaging", "channel_subscription", "heartbeat_ping_pong"],
    })


async def websocket_stream_handler(websocket: WebSocket) -> None:
    """Core WebSocket handler for duplex real-time streaming."""
    await websocket.accept()
    await websocket.send_json({
        "type": "connected",
        "protocol": "airops-nexus-ws-v1",
        "message": "WebSocket real-time stream established",
        "as_of": get_clock().now().isoformat(),
    })

    pubsub = None
    try:
        pubsub = redis_client.pubsub()
        pubsub.subscribe("jobs:progress", "alerts:new", "events:ingested", "telemetry:update")
    except Exception as exc:
        logger.warning("WebSocket: Redis pubsub unavailable, running without redis", exc_info=exc)

    async def receive_client_messages():
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    payload = json.loads(msg_text)
                    action = payload.get("action")
                    if action == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": get_clock().now().isoformat(),
                        })
                    elif action == "subscribe" and pubsub and payload.get("channel"):
                        pubsub.subscribe(payload["channel"])
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": payload["channel"],
                        })
                    elif action == "echo":
                        await websocket.send_json({
                            "type": "echo",
                            "payload": payload.get("payload"),
                        })
                except json.JSONDecodeError:
                    if msg_text.strip().lower() == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": get_clock().now().isoformat(),
                        })
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def send_redis_updates():
        try:
            while True:
                if pubsub:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                    if message and message.get("type") == "message":
                        channel = message.get("channel", "update")
                        raw_data = message.get("data", "{}")
                        try:
                            parsed_data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                        except Exception:
                            parsed_data = raw_data
                        await websocket.send_json({
                            "type": "message",
                            "channel": channel,
                            "data": parsed_data,
                        })
                await asyncio.sleep(0.2)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    sender_task = asyncio.create_task(send_redis_updates())
    receiver_task = asyncio.create_task(receive_client_messages())

    done, pending = await asyncio.wait(
        [sender_task, receiver_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    if pubsub:
        try:
            pubsub.close()
        except Exception:
            pass


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Duplex WebSocket endpoint at /api/v1/ws streaming live progress, alerts, and telemetry."""
    await websocket_stream_handler(websocket)
