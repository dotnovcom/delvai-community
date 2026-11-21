import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.quota import consume_quota, rollback_quota
from app.models.user import User
from app.schemas.conversation import (
    ChatStreamRequest,
    ConversationCreate,
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
    TranscriptRequest,
    RegenerateRequest,
    SendMessageRequest,
)
from app.services import conversation_service

router = APIRouter()


@router.get("/ai-ui")
def get_ai_chat_ui(db: Session = Depends(get_db)):
    from app.services.chat_action_service import ai_chat_ui

    return ai_chat_ui(db)


@router.get("/shares/{token}")
def read_shared_message(token: str, db: Session = Depends(get_db)):
    from app.services.chat_action_service import get_share

    share = get_share(db, token)
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在或已失效")
    from app.utils.legal_content import polish_legal_assistant_content

    return {
        "question": polish_legal_assistant_content(share.question),
        "answer": polish_legal_assistant_content(share.answer),
        "created_at": share.created_at,
    }


def _conv_to_response(conv, db: Session) -> ConversationResponse:
    messages = conversation_service.list_messages(db, conv.id)
    last_msg = None
    for row in reversed(messages):
        if row.role.value == "assistant" and row.content:
            last_msg = row.content
            break
    if last_msg is None and messages:
        last_msg = messages[-1].content
    if last_msg:
        last_msg = " ".join(last_msg.split())[:80]
    resp = ConversationResponse.model_validate(conv)
    resp.last_message = last_msg
    return resp


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = conversation_service.create_conversation(db, current_user, body)
    return _conv_to_response(conv, db)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    skip: int = 0,
    limit: int = 20,
    types: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.conversation import InteractionType

    wanted = None
    if types:
        wanted = []
        for raw in types.split(","):
            key = raw.strip().lower()
            if key in {item.value for item in InteractionType}:
                wanted.append(InteractionType(key))
    convs = conversation_service.list_conversations(db, current_user, skip, limit, wanted)
    return [_conv_to_response(c, db) for c in convs]


@router.post("/{conversation_id}/transcript", response_model=MessageResponse)
def save_transcript(
    conversation_id: int,
    body: TranscriptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = conversation_service.append_transcript(
        db, current_user, conversation_id, body.role, body.content, body.title
    )
    if not msg:
        raise HTTPException(status_code=404, detail="对话不存在")
    return MessageResponse.model_validate(msg)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = conversation_service.get_conversation(db, current_user, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    rows = conversation_service.list_messages(db, conversation_id)
    from app.services.chat_action_service import feedback_map

    votes = feedback_map(db, current_user.id, [row.id for row in rows])
    result = []
    for row in rows:
        item = MessageResponse.model_validate(row)
        vote = votes.get(row.id)
        if vote in ("like", "dislike"):
            item.my_feedback = vote
        result.append(item)
    return result


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not conversation_service.delete_conversation(db, current_user, conversation_id):
        raise HTTPException(status_code=404, detail="对话不存在")


async def _sse_generator(
    db: Session,
    conv,
    body: SendMessageRequest,
    *,
    user_id: int,
    consume_source: str = "",
    reuse_user_message=None,
    bypass_cache: bool = False,
) -> AsyncGenerator[str, None]:
    stream_ok = False
    try:
        async for event in conversation_service.generate_ai_stream(
            db,
            conv,
            body,
            reuse_user_message=reuse_user_message,
            bypass_cache=bypass_cache,
        ):
            if event.get("type") == "error":
                if not stream_ok:
                    rollback_quota(db, user_id, "daily_chat", consume_source=consume_source)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                break
            stream_ok = True
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
    except Exception as e:
        if not stream_ok:
            rollback_quota(db, user_id, "daily_chat", consume_source=consume_source)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/{conversation_id}/messages")
async def send_message_stream(
    conversation_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = conversation_service.get_conversation(db, current_user, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    from app.services.content_moderation import moderate_text
    passed, reason = moderate_text(db, body.content)
    if not passed:
        raise HTTPException(status_code=400, detail=reason or "内容未通过审核")

    consume_result = consume_quota(db, current_user.id, "daily_chat")

    return StreamingResponse(
        _sse_generator(
            db,
            conv,
            body,
            user_id=current_user.id,
            consume_source=consume_result.consume_source,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _owned_assistant(db: Session, user: User, conversation_id: int, message_id: int):
    from app.models.message import Message, MessageRole

    conv = conversation_service.get_conversation(db, user, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    message = (
        db.query(Message)
        .filter(Message.id == message_id, Message.conversation_id == conversation_id)
        .first()
    )
    if not message or message.role != MessageRole.ASSISTANT:
        raise HTTPException(status_code=404, detail="回复不存在")
    return conv, message


@router.post("/{conversation_id}/messages/{message_id}/feedback")
def set_message_feedback(
    conversation_id: int,
    message_id: int,
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.chat_action_service import action_enabled, set_feedback

    key = "ai_action_like" if body.vote == "like" else "ai_action_dislike"
    if body.vote != "none" and not action_enabled(db, key):
        raise HTTPException(status_code=403, detail="该操作已关闭")
    _, message = _owned_assistant(db, current_user, conversation_id, message_id)
    vote = None if body.vote == "none" else body.vote
    saved = set_feedback(db, current_user, message, vote)
    return {"vote": saved}


@router.post("/{conversation_id}/messages/{message_id}/share")
def share_message(
    conversation_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.chat_action_service import action_enabled, create_share

    if not action_enabled(db, "ai_action_share"):
        raise HTTPException(status_code=403, detail="分享已关闭")
    _, message = _owned_assistant(db, current_user, conversation_id, message_id)
    share = create_share(db, current_user, message)
    return {"token": share.token, "path": f"/share/{share.token}"}


@router.post("/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    conversation_id: int,
    message_id: int,
    body: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.chat_action_service import action_enabled

    if not action_enabled(db, "ai_action_regenerate"):
        raise HTTPException(status_code=403, detail="重新生成已关闭")
    conv, _message = _owned_assistant(db, current_user, conversation_id, message_id)
    consume_result = consume_quota(db, current_user.id, "daily_chat")
    try:
        user_msg = conversation_service.prepare_regenerate(db, conversation_id, message_id)
    except ValueError as e:
        rollback_quota(db, current_user.id, "daily_chat", consume_source=consume_result.consume_source)
        raise HTTPException(status_code=400, detail=str(e)) from e

    meta = user_msg.metadata_ or {}
    content_type = user_msg.content_type.value if hasattr(user_msg.content_type, "value") else user_msg.content_type
    send_body = SendMessageRequest(
        content=user_msg.content or "请继续",
        content_type=content_type if content_type in ("text", "image", "file") else "text",
        image_url=meta.get("image_url"),
        file_url=meta.get("file_url"),
        file_name=meta.get("file_name"),
        deep_think=body.deep_think,
        online_search=body.online_search,
    )
    return StreamingResponse(
        _sse_generator(
            db,
            conv,
            send_body,
            user_id=current_user.id,
            consume_source=consume_result.consume_source,
            reuse_user_message=user_msg,
            bypass_cache=True,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload-image")
async def upload_chat_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services import upload_service

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")
    url = await upload_service.save_upload(db, file, subdir="chat")
    return {"url": url}


@router.post("/upload-file")
async def upload_chat_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services import upload_service

    if file.content_type and file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请使用 upload-image 上传图片")
    try:
        url = await upload_service.save_upload(db, file, subdir="chat")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"url": url, "filename": file.filename or "file"}
