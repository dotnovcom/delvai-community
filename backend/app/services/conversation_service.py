import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, ConversationStatus, InteractionType
from app.models.message import ContentType, Message, MessageRole
from app.models.user import User
from app.schemas.conversation import ConversationCreate, SendMessageRequest
from app.services.ai.router import (
    build_messages,
    generate_suggestions,
    route_engine,
    stream_response,
)


def create_conversation(db: Session, user: User, data: ConversationCreate) -> Conversation:
    conv = Conversation(
        user_id=user.id,
        title=data.title or "新对话",
        interaction_type=InteractionType(data.interaction_type),
        status=ConversationStatus.ACTIVE,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_conversations(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 20,
    types: list[InteractionType] | None = None,
) -> list[Conversation]:
    if types and any(t in (InteractionType.VOICE, InteractionType.VIDEO) for t in types):
        from commercial.services.legal_demo_seed import ensure_user_media_demos

        ensure_user_media_demos(db, user.id)
    q = db.query(Conversation).filter(
        Conversation.user_id == user.id,
        Conversation.status != ConversationStatus.DELETED,
    )
    if types:
        q = q.filter(Conversation.interaction_type.in_(types))
    return q.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()


def get_conversation(db: Session, user: User, conversation_id: int) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
            Conversation.status != ConversationStatus.DELETED,
        )
        .first()
    )


def append_transcript(
    db: Session,
    user: User,
    conversation_id: int,
    role: str,
    content: str,
    title: str | None = None,
) -> Message | None:
    conv = get_conversation(db, user, conversation_id)
    text = (content or "").strip()
    if not conv or not text:
        return None
    if title and conv.title in {"新对话", "语音咨询", "视频咨询"}:
        conv.title = title.strip()[:256]
    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER if role == "user" else MessageRole.ASSISTANT,
        content_type=ContentType.TEXT,
        content=text,
    )
    conv.updated_at = datetime.now(timezone.utc)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def delete_conversation(db: Session, user: User, conversation_id: int) -> bool:
    conv = get_conversation(db, user, conversation_id)
    if not conv:
        return False
    conv.status = ConversationStatus.DELETED
    db.commit()
    return True


def list_messages(db: Session, conversation_id: int) -> list[Message]:
    from app.services.pii_mask import mask_text
    from app.utils.legal_content import polish_legal_assistant_content

    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    for row in rows:
        if row.content and row.role == MessageRole.ASSISTANT:
            row.content = polish_legal_assistant_content(row.content)
        if row.content:
            row.content = mask_text(db, row.content)
    return rows


def prepare_regenerate(db: Session, conversation_id: int, message_id: int) -> Message:
    """删除指定 AI 回复，返回它对应的用户提问，供重新生成。"""
    assistant = (
        db.query(Message)
        .filter(Message.id == message_id, Message.conversation_id == conversation_id)
        .first()
    )
    if not assistant or assistant.role != MessageRole.ASSISTANT:
        raise ValueError("只能重新生成 AI 回复")
    user_msg = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.USER,
            Message.id < assistant.id,
        )
        .order_by(Message.id.desc())
        .first()
    )
    if not user_msg:
        raise ValueError("找不到对应的提问")
    db.delete(assistant)
    db.commit()
    db.refresh(user_msg)
    return user_msg


def _auto_title(content: str) -> str:
    title = content.strip().replace("\n", " ")[:30]
    return title or "新对话"


def save_user_message(
    db: Session,
    conversation: Conversation,
    data: SendMessageRequest,
) -> Message:
    metadata = {}
    if data.file_name:
        metadata["file_name"] = data.file_name
    if data.file_url:
        metadata["file_url"] = data.file_url
    if data.image_url:
        metadata["image_url"] = data.image_url

    msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content_type=ContentType(data.content_type),
        content=data.content,
        metadata_=metadata or None,
    )
    db.add(msg)

    if conversation.title == "新对话":
        conversation.title = _auto_title(data.content)

    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


def _generating_draft(db: Session, conversation_id: int) -> Message | None:
    draft = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
        )
        .order_by(Message.id.desc())
        .first()
    )
    if not draft:
        return None
    meta = draft.metadata_ or {}
    if meta.get("generating"):
        return draft
    return None


def upsert_stream_draft(
    db: Session,
    conversation: Conversation,
    content: str,
    ai_engine: str,
) -> Message:
    """生成过程中先落库，刷新页面也能看到已经写出的内容。"""
    text = (content or "").strip()
    draft = _generating_draft(db, conversation.id)
    now = datetime.now(timezone.utc)
    if draft:
        draft.content = text
        draft.ai_engine = ai_engine
        conversation.updated_at = now
        db.commit()
        return draft
    msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content_type=ContentType.TEXT,
        content=text,
        ai_engine=ai_engine,
        metadata_={"generating": True},
    )
    db.add(msg)
    conversation.updated_at = now
    db.commit()
    db.refresh(msg)
    return msg


def finish_assistant_message(
    db: Session,
    conversation: Conversation,
    content: str,
    ai_engine: str,
    tokens_used: int,
    suggestions: list[str],
    *,
    interrupted: bool = False,
) -> Message:
    draft = _generating_draft(db, conversation.id)
    now = datetime.now(timezone.utc)
    meta: dict = {"interrupted": True} if interrupted else {"suggestions": suggestions}
    if draft:
        draft.content = content
        draft.tokens_used = tokens_used
        draft.ai_engine = ai_engine
        draft.metadata_ = meta
        conversation.updated_at = now
        db.commit()
        db.refresh(draft)
        return draft
    if interrupted:
        msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content_type=ContentType.TEXT,
            content=content,
            tokens_used=tokens_used,
            ai_engine=ai_engine,
            metadata_=meta,
        )
        db.add(msg)
        conversation.updated_at = now
        db.commit()
        db.refresh(msg)
        return msg
    return save_assistant_message(db, conversation, content, ai_engine, tokens_used, suggestions)


def save_assistant_message(
    db: Session,
    conversation: Conversation,
    content: str,
    ai_engine: str,
    tokens_used: int,
    suggestions: list[str],
) -> Message:
    msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content_type=ContentType.TEXT,
        content=content,
        tokens_used=tokens_used,
        ai_engine=ai_engine,
        metadata_={"suggestions": suggestions},
    )
    db.add(msg)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


def get_history_for_ai(messages: list[Message]) -> list[dict]:
    history = []
    for msg in messages:
        if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
            history.append({"role": msg.role.value, "content": msg.content})
    return history


def _split_stream_tokens(text: str, size: int = 2) -> list[str]:
    """将上游大块拆成小片段，模拟 incremental_output 的逐字效果。"""
    if not text:
        return []
    if len(text) <= size:
        return [text]
    return [text[i : i + size] for i in range(0, len(text), size)]


async def generate_ai_stream(
    db: Session,
    conversation: Conversation,
    data: SendMessageRequest,
    *,
    reuse_user_message: Message | None = None,
    bypass_cache: bool = False,
):
    """生成 AI 流式响应的 async generator，yield dict 事件。"""
    if reuse_user_message is not None:
        user_msg = reuse_user_message
    else:
        user_msg = save_user_message(db, conversation, data)
    prior_messages = list_messages(db, conversation.id)
    history = get_history_for_ai(prior_messages[:-1])

    ai_content = data.content
    if data.file_url and data.content_type == "file":
        yield {"type": "status", "content": "正在解析附件正文…"}
        from app.services.chat_attachment_service import try_resolve_ai_content

        ai_content = await try_resolve_ai_content(db, data)

    engine = route_engine(
        content=data.content,
        content_type=data.content_type,
        has_image=bool(data.image_url),
        history_length=len(history),
    )

    from commercial.services.semantic_cache import get_cached, set_cached

    cached = None if bypass_cache else get_cached(db, engine, data.content)
    if cached and not data.image_url and not data.file_url:
        yield {"type": "start", "engine": engine, "user_message_id": user_msg.id, "cached": True}
        from app.utils.legal_content import polish_legal_assistant_content

        full_content = polish_legal_assistant_content(cached.get("content") or "")
        from app.utils.legal_content import split_legal_answer

        summary, detail = split_legal_answer(full_content)
        if summary:
            yield {"type": "replace", "content": summary}
        if detail:
            yield {"type": "detail", "content": detail}
        suggestions = cached.get("suggestions") or generate_suggestions(full_content, engine)
        assistant_msg = save_assistant_message(
            db, conversation, full_content, engine, cached.get("tokens_used") or 0, suggestions
        )
        from app.services.ai_usage_service import chat_service_key, log_ai_usage

        log_ai_usage(
            db,
            user_id=conversation.user_id,
            service_key=chat_service_key(conversation.interaction_type),
            ai_engine=engine,
            total_tokens=cached.get("tokens_used") or 0,
            ref_type="message",
            ref_id=assistant_msg.id,
        )
        yield {
            "type": "done",
            "message_id": assistant_msg.id,
            "ai_engine": engine,
            "tokens_used": cached.get("tokens_used") or 0,
            "suggestions": suggestions,
            "conversation_title": conversation.title,
            "cached": True,
        }
        return

    ai_messages = build_messages(history, ai_content)

    yield {
        "type": "start",
        "engine": engine,
        "user_message_id": user_msg.id,
    }

    from app.utils.legal_content import polish_legal_assistant_content, prepare_stream_snapshot, split_legal_answer

    raw_content = ""
    tokens_used = 0
    visible_summary = ""
    visible_detail = ""
    last_saved = ""
    last_save_at = 0.0

    def persist_partial(force: bool = False) -> None:
        nonlocal last_saved, last_save_at
        snapshot = prepare_stream_snapshot(raw_content).strip()
        if not snapshot or snapshot == last_saved:
            return
        now = asyncio.get_running_loop().time()
        if not force and last_saved and now - last_save_at < 0.35 and len(snapshot) - len(last_saved) < 24:
            return
        try:
            upsert_stream_draft(db, conversation, snapshot, engine)
        except Exception:
            db.rollback()
            return
        last_saved = snapshot
        last_save_at = now

    try:
        async for chunk, tokens, status in stream_response(
            engine,
            ai_messages,
            data.image_url,
            db=db,
            deep_think=data.deep_think,
            online_search=data.online_search,
        ):
            if status:
                yield {"type": "status", "content": status}
                await asyncio.sleep(0)
            if chunk:
                from app.services.ai.stream_marks import FULL_REPLACE_PREFIX

                if chunk.startswith(FULL_REPLACE_PREFIX):
                    raw_content = chunk[len(FULL_REPLACE_PREFIX) :]
                else:
                    raw_content += chunk
                summary, detail = split_legal_answer(prepare_stream_snapshot(raw_content))
                if summary and summary != visible_summary:
                    if visible_summary and summary.startswith(visible_summary):
                        delta = summary[len(visible_summary) :]
                        if delta:
                            yield {"type": "token", "content": delta}
                            visible_summary = summary
                    elif not (visible_summary and visible_summary.startswith(summary)):
                        yield {"type": "replace", "content": summary}
                        visible_summary = summary
                if detail and detail != visible_detail:
                    yield {"type": "detail", "content": detail}
                    visible_detail = detail
                persist_partial()
            if tokens:
                tokens_used = tokens
    except asyncio.CancelledError:
        snapshot = prepare_stream_snapshot(raw_content).strip()
        if snapshot:
            finish_assistant_message(
                db,
                conversation,
                snapshot,
                engine,
                tokens_used,
                [],
                interrupted=True,
            )
        raise

    full_content = polish_legal_assistant_content(raw_content)
    _summary, final_detail = split_legal_answer(full_content)
    if final_detail and final_detail != visible_detail:
        yield {"type": "detail", "content": final_detail}
        visible_detail = final_detail

    if not tokens_used:
        from app.services.ai.router import estimate_tokens
        tokens_used = estimate_tokens(full_content)

    suggestions = generate_suggestions(full_content, engine)
    assistant_msg = finish_assistant_message(
        db, conversation, full_content, engine, tokens_used, suggestions
    )

    from app.services.ai_usage_service import chat_service_key, log_ai_usage

    log_ai_usage(
        db,
        user_id=conversation.user_id,
        service_key=chat_service_key(conversation.interaction_type),
        ai_engine=engine,
        total_tokens=tokens_used,
        ref_type="message",
        ref_id=assistant_msg.id,
    )

    if not data.image_url and not data.file_url:
        set_cached(
            db,
            engine,
            data.content,
            {"content": full_content, "suggestions": suggestions, "tokens_used": tokens_used},
        )

    yield {
        "type": "done",
        "message_id": assistant_msg.id,
        "ai_engine": engine,
        "tokens_used": tokens_used,
        "suggestions": suggestions,
        "conversation_title": conversation.title,
    }
