from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import ArtifactPaths, SeasonGapAnalysisRequest


class SpecialistSeasonInput(BaseModel):
    season_a_label: str = Field(description="Season label in the format YYYY-season.")
    season_b_label: str = Field(description="Season label in the format YYYY-season.")
    page_limit: int = Field(ge=1, le=20)
    per_page: int = Field(ge=1, le=100)
    min_rating_total: int = Field(ge=0)
    top_n: int = Field(ge=1, le=20, default=5)
    output_subdir: str | None = None


class HypothesisToolInput(BaseModel):
    retrieval_summary: str
    eda_summary: str


class AgentSeasonGapResponse(BaseModel):
    mode: Literal["agent"] = "agent"
    request: SeasonGapAnalysisRequest
    orchestrator_output: str
    critic_verdict: Literal["PASS", "REVISE", "UNKNOWN"]
    critic_feedback: str
    final_report: str
    artifacts: ArtifactPaths | None = None
