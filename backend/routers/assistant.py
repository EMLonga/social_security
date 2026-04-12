from fastapi import APIRouter, Depends, HTTPException

from config import settings
from models import User
from schemas import AssistantChatRequest, AssistantChatResponse
from security import get_optional_user
from services.llm_service import LLMServiceError, chat_completion

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _build_system_prompt(language: str) -> str:
    if language == "zh":
        return (
            "你是社区安全预警网站的站内助手。"
            "请用通俗、简洁、可执行的方式回答，优先解释页面功能、图表指标、按钮用途和操作路径。"
            "不要编造后端不存在的功能。"
            "当用户问不清楚时，先给可用解释，再提示用户补充页面元素文字。"
        )
    return (
        "You are the in-site assistant for a community safety alert website. "
        "Respond in plain, concise, actionable language. "
        "Prioritize explaining page features, charts/metrics, button purpose, and exact navigation steps. "
        "Do not invent unavailable features."
    )


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    payload: AssistantChatRequest,
    current_user: User | None = Depends(get_optional_user),
):
    role = "guest"
    if current_user:
        role = "admin" if getattr(current_user.role, "value", str(current_user.role)) == "admin" else "user"
    elif payload.role in {"guest", "user", "admin"}:
        role = payload.role

    page_explain_lines = payload.page_explain or []
    page_explain_text = "\n".join([f"- {line}" for line in page_explain_lines[:8]])
    context_text = (
        f"language={payload.language}\n"
        f"user_role={role}\n"
        f"page_name={payload.page_name or 'unknown'}\n"
        f"page_path={payload.page_path or 'unknown'}\n"
        f"page_summary={payload.page_summary or 'N/A'}\n"
        f"page_explain:\n{page_explain_text or '- N/A'}"
    )

    messages = [
        {"role": "system", "content": _build_system_prompt(payload.language)},
        {"role": "system", "content": f"Current page context:\n{context_text}"},
        {"role": "user", "content": payload.message},
    ]

    try:
        reply = chat_completion(messages)
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AssistantChatResponse(reply=reply, model=settings.LLM_MODEL)
