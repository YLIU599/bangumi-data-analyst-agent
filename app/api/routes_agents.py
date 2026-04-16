from fastapi import APIRouter, Depends, HTTPException

from app.agents.models import AgentSeasonGapResponse
from app.agents.service import run_agent_season_gap_analysis
from app.bangumi.client import BangumiAPIError
from app.core.config import Settings, get_settings
from app.schemas import SeasonGapAnalysisRequest

router = APIRouter(tags=["agent-analysis"])


@router.post("/agent/season-gap", response_model=AgentSeasonGapResponse)
async def analyze_season_gap_with_agents(
    request: SeasonGapAnalysisRequest,
    settings: Settings = Depends(get_settings),
) -> AgentSeasonGapResponse:
    try:
        return await run_agent_season_gap_analysis(request=request, settings=settings)
    except BangumiAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
