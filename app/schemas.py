from typing import Literal

from pydantic import BaseModel, Field


SeasonName = Literal["winter", "spring", "summer", "fall"]


class SeasonRef(BaseModel):
    year: int = Field(ge=1900, le=2100)
    season: SeasonName

    @property
    def label(self) -> str:
        return f"{self.year}-{self.season}"


class SeasonGapAnalysisRequest(BaseModel):
    season_a: SeasonRef
    season_b: SeasonRef
    page_limit: int = Field(default=4, ge=1, le=20)
    per_page: int = Field(default=25, ge=1, le=100)
    top_n: int = Field(default=5, ge=1, le=20)
    min_rating_total: int = Field(default=30, ge=0)
    output_subdir: str | None = None


class GapRecord(BaseModel):
    subject_id: int
    name: str
    name_cn: str | None = None
    season_label: str
    air_date: str | None = None
    score: float
    rating_total: int
    popularity_log10: float
    gap: float


class CohortSummary(BaseModel):
    season_label: str
    n_titles: int
    avg_score: float
    avg_rating_total: float
    avg_gap: float
    median_gap: float
    top_positive_gap_titles: list[GapRecord]
    top_negative_gap_titles: list[GapRecord]


class ComparisonSummary(BaseModel):
    higher_scoring_season: str | None = None
    higher_popularity_season: str | None = None
    largest_gap_title: GapRecord | None = None
    hypothesis: str


class ArtifactPaths(BaseModel):
    run_dir: str
    combined_csv: str
    summary_json: str
    scatter_plot_png: str


class SeasonGapAnalysisResponse(BaseModel):
    request: SeasonGapAnalysisRequest
    combined_n_titles: int
    cohorts: list[CohortSummary]
    comparison: ComparisonSummary
    artifacts: ArtifactPaths
