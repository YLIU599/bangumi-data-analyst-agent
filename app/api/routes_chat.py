from fastapi import APIRouter, Depends, HTTPException

from app.bangumi.client import BangumiAPIError
from app.chat.service import answer_bangumi_question
from app.core.config import Settings, get_settings
from app.schemas import BangumiChatRequest, BangumiChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat/season-gap", response_model=BangumiChatResponse)
async def chat_about_season_gap(
    request: BangumiChatRequest,
    settings: Settings = Depends(get_settings),
) -> BangumiChatResponse:
    try:
        return await answer_bangumi_question(request=request, settings=settings)
    except BangumiAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
