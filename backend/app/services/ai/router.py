import re
from collections.abc import AsyncGenerator
from enum import Enum

from app.models.message import AIEngine
from app.services.ai import deepseek

try:
    from commercial.services.ai import farui, multimodal
except ImportError:
    farui = None
    multimodal = None

COMPLEX_KEYWORDS = [
    "分析", "推理", "对比", "策略", "权衡", "利弊", "如何应对",
    "胜诉", "辩护", "复杂", "多个", "竞合", "风险", "方案",
    "怎么办", "能不能", "是否应该", "是否合法",
]

SEARCH_KEYWORDS = [
    "检索", "查找", "搜索", "法规", "案例", "条文", "判例", "法条",
]

IMAGE_CONTENT_TYPES = {"image"}


class RouteDecision(str, Enum):
    FARUI = AIEngine.FARUI.value
    DEEPSEEK = AIEngine.DEEPSEEK.value
    QWEN_VL = AIEngine.QWEN_VL.value


def route_engine(
    content: str,
    content_type: str = "text",
    has_image: bool = False,
    history_length: int = 0,
) -> str:
    if farui is None and multimodal is None:
        return RouteDecision.DEEPSEEK.value
    if (content_type in IMAGE_CONTENT_TYPES or has_image) and multimodal is not None:
        return RouteDecision.QWEN_VL.value

    text = content.strip()
    if any(kw in text for kw in SEARCH_KEYWORDS):
        return RouteDecision.FARUI.value

    complex_score = sum(1 for kw in COMPLEX_KEYWORDS if kw in text)
    if complex_score >= 2 or len(text) > 200 or history_length > 6:
        return RouteDecision.DEEPSEEK.value

    if any(kw in text for kw in COMPLEX_KEYWORDS):
        return RouteDecision.DEEPSEEK.value

    return RouteDecision.FARUI.value


def build_messages(history: list[dict], user_content: str) -> list[dict]:
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_content})
    return messages


def generate_suggestions(content: str, engine: str) -> list[str]:
    suggestions = []
    if "合同" in content:
        suggestions.extend(["合同有哪些常见风险点？", "如何修改不利条款？"])
    elif "劳动" in content or "工伤" in content:
        suggestions.extend(["劳动仲裁流程是什么？", "如何收集证据？"])
    elif "离婚" in content or "婚姻" in content:
        suggestions.extend(["财产如何分割？", "子女抚养权如何判定？"])
    else:
        suggestions.extend(["相关法规有哪些？", "类似案例怎么处理？"])

    if engine == RouteDecision.DEEPSEEK.value:
        suggestions.append("请给出更详细的策略分析")
    else:
        suggestions.append("请检索相关法条")

    return suggestions[:3]


def estimate_tokens(text: str) -> int:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = len(text) - chinese
    return chinese + max(other // 4, 1)


async def stream_response(
    engine: str,
    messages: list[dict],
    image_url: str | None = None,
    db=None,
    *,
    deep_think: bool = True,
    online_search: bool = True,
) -> AsyncGenerator[tuple[str, int, str | None], None]:
    total_tokens = 0
    if engine == RouteDecision.QWEN_VL.value and multimodal is not None:
        stream = multimodal.stream_chat(messages, image_url, db=db)
    elif engine == RouteDecision.DEEPSEEK.value or farui is None:
        stream = deepseek.stream_chat(messages, db=db)
    else:
        stream = farui.stream_chat(
            messages,
            db=db,
            deep_think=deep_think,
            online_search=online_search,
        )

    async for item in stream:
        if len(item) == 3:
            chunk, tokens, status = item
        else:
            chunk, tokens = item  # type: ignore[misc]
            status = None
        if tokens:
            total_tokens = tokens
        yield chunk, total_tokens, status
