import json
from collections.abc import AsyncGenerator

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.quota import consume_quota, rollback_quota
from app.models.user import User
from app.schemas.conversation import ChatStreamRequest, SendMessageRequest
from app.services import conversation_service

router = APIRouter()


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = conversation_service.get_conversation(db, current_user, body.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    consume_result = consume_quota(db, current_user.id, "daily_chat")

    send_body = SendMessageRequest(
        content=body.content,
        content_type=body.content_type,
        image_url=body.image_url,
        file_name=body.file_name,
    )

    async def event_gen() -> AsyncGenerator[str, None]:
        stream_ok = False
        try:
            async for event in conversation_service.generate_ai_stream(db, conv, send_body):
                if event.get("type") == "error":
                    if not stream_ok:
                        rollback_quota(
                            db,
                            current_user.id,
                            "daily_chat",
                            consume_source=consume_result.consume_source,
                        )
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    break
                stream_ok = True
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)
        except Exception as e:
            if not stream_ok:
                rollback_quota(
                    db,
                    current_user.id,
                    "daily_chat",
                    consume_source=consume_result.consume_source,
                )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
