import asyncio

import logging

from collections.abc import AsyncGenerator



import httpx

from sqlalchemy.orm import Session



from app.core.ai_config import use_ai_mock

from app.core.database import SessionLocal

from app.services.ai.sse_parser import parse_sse_data_line

from app.services.integration_config import get_ai_integration



logger = logging.getLogger(__name__)





def _resolve(db: Session | None) -> tuple[Session, bool]:

    if db is not None:

        return db, False

    return SessionLocal(), True





async def stream_chat(

    messages: list[dict],

    db: Session | None = None,

) -> AsyncGenerator[tuple[str, int], None]:

    session, close = _resolve(db)

    try:

        cfg = get_ai_integration(session, "deepseek")

        api_key = cfg.get("api_key")

        if not use_ai_mock(api_key, session):

            async for chunk, tokens in _stream_deepseek_real(messages, cfg):

                yield chunk, tokens

            return

        async for chunk, tokens in _stream_deepseek_mock(messages):

            yield chunk, tokens

    finally:

        if close:

            session.close()





async def _stream_deepseek_mock(messages: list[dict]) -> AsyncGenerator[tuple[str, int], None]:

    user_msg = messages[-1]["content"] if messages else ""

    response = (

        f"【DeepSeek 深度分析】针对您的复杂问题「{user_msg[:50]}」，"

        f"我从多个维度进行推理：\n\n"

        f"**事实梳理**\n"

        f"需要先厘清事件的时间线、参与主体及核心争议焦点。\n\n"

        f"**法律适用**\n"

        f"可能涉及多个法律规范的竞合，需逐一分析各规范的适用条件。\n\n"

        f"**策略建议**\n"

        f"• 协商路径：成本较低，可优先尝试\n"

        f"• 诉讼路径：需评估胜诉概率及执行风险\n"

        f"• 证据准备：建议系统整理书证、物证及电子数据\n\n"

        f"**风险提示**\n"

        f"复杂案件存在不确定性，建议结合具体证据进一步分析。"

    )

    tokens = len(response) // 2

    for i, char in enumerate(response):

        yield char, tokens if i == len(response) - 1 else 0

        await asyncio.sleep(0.015)





async def _stream_deepseek_real(

    messages: list[dict],

    cfg: dict,

) -> AsyncGenerator[tuple[str, int], None]:

    base = cfg.get("base_url") or "https://api.deepseek.com/v1"

    model = (cfg.get("extra") or {}).get("model") or "deepseek-v4-pro"

    url = f"{base.rstrip('/')}/chat/completions"

    headers = {

        "Authorization": f"Bearer {cfg['api_key']}",

        "Content-Type": "application/json",

    }

    payload = {

        "model": model,

        "messages": messages,

        "stream": True,

    }

    total_tokens = 0

    async with httpx.AsyncClient(timeout=120) as client:

        async with client.stream("POST", url, headers=headers, json=payload) as resp:

            resp.raise_for_status()

            async for line in resp.aiter_lines():

                if not line.startswith("data:"):

                    continue

                data = line[5:].strip()

                if data == "[DONE]":

                    break

                text, tokens = parse_sse_data_line(data)

                if tokens:

                    total_tokens = tokens

                if text:

                    yield text, 0

    yield "", total_tokens


async def complete(
    messages: list[dict],
    system_prompt: str | None = None,
    db: Session | None = None,
    *,
    model: str | None = None,
) -> tuple[str, int]:
    """非流式补全（文书生成、开放 API 等）。"""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + list(messages)
    session, close = _resolve(db)
    try:
        cfg = get_ai_integration(session, "deepseek")
        api_key = cfg.get("api_key")
        if not use_ai_mock(api_key, session):
            extra = cfg.get("extra") or {}
            m = model or extra.get("model") or "deepseek-v4-pro"
            cfg = {**cfg, "extra": {**extra, "model": m}}
            return await _complete_deepseek_real(messages, cfg)
        return await _complete_deepseek_mock(messages)
    finally:
        if close:
            session.close()


async def _complete_deepseek_real(messages: list[dict], cfg: dict) -> tuple[str, int]:
    base = cfg.get("base_url") or "https://api.deepseek.com/v1"
    model = (cfg.get("extra") or {}).get("model") or "deepseek-v4-pro"
    url = f"{base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    }
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return content, tokens


async def _complete_deepseek_mock(messages: list[dict]) -> tuple[str, int]:
    user_msg = messages[-1]["content"] if messages else ""
    return (
        f"【DeepSeek Mock】已根据指令生成文书草案（{len(user_msg)} 字上下文）。\n\n"
        "一、当事人\n（请填写）\n\n二、事实与理由\n（请填写）\n\n三、诉讼请求\n（请填写）",
        200,
    )


