from fastapi import APIRouter, Depends, HTTPException

from app.analysis.season_gap import run_season_gap_analysis
from app.bangumi.client import BangumiAPIError, BangumiClient
from app.core.config import Settings, get_settings
from app.schemas import SeasonGapAnalysisRequest, SeasonGapAnalysisResponse

router = APIRouter(tags=["analysis"])


@router.post("/analysis/season-gap", response_model=SeasonGapAnalysisResponse)
async def analyze_season_gap(
    request: SeasonGapAnalysisRequest,
    settings: Settings = Depends(get_settings),
) -> SeasonGapAnalysisResponse:
    try:
        async with BangumiClient(settings) as client:
            return await run_season_gap_analysis(
                client=client,
                request=request,
                settings=settings,
            )
    except BangumiAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
