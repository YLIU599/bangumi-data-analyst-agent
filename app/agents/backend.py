from __future__ import annotations

from typing import Any

from app.analysis.season_gap import (
    normalize_subject,
    run_season_gap_analysis_from_prefetched_rows,
    season_to_start_month,
)
from app.bangumi.client import BangumiClient
from app.core.config import Settings
from app.schemas import SeasonGapAnalysisRequest, SeasonGapAnalysisResponse, SeasonRef


class AgentWorkflowBackend:
    """Direct bindings to the existing Bangumi retrieval path and prefetched-row analysis path."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.latest_analysis_response: SeasonGapAnalysisResponse | None = None
        self.prefetched_rows_by_season: dict[str, list[dict[str, Any]]] = {}

    @staticmethod
    def parse_season_label(label: str) -> SeasonRef:
        try:
            year_text, season = label.strip().split("-", 1)
            return SeasonRef(year=int(year_text), season=season)
        except Exception as exc:
            raise ValueError(
                f"Invalid season label '{label}'. Expected format YYYY-winter|spring|summer|fall."
            ) from exc

    async def fetch_runtime_season_snapshots(
        self,
        *,
        season_a_label: str,
        season_b_label: str,
        page_limit: int,
        per_page: int,
        min_rating_total: int,
    ) -> dict[str, Any]:
        season_refs = [
            self.parse_season_label(season_a_label),
            self.parse_season_label(season_b_label),
        ]

        async with BangumiClient(self.settings) as client:
            snapshots = []
            for season_ref in season_refs:
                raw_items = await client.fetch_season_subjects(
                    year=season_ref.year,
                    month=season_to_start_month(season_ref),
                    page_limit=page_limit,
                    per_page=per_page,
                )

                rows: list[dict[str, Any]] = []
                for item in raw_items:
                    normalized = normalize_subject(item, season_ref.label)
                    if normalized is None:
                        continue
                    if normalized["rating_total"] < min_rating_total:
                        continue
                    rows.append(normalized)

                self.prefetched_rows_by_season[season_ref.label] = rows

                by_rating = sorted(rows, key=lambda row: row["rating_total"], reverse=True)[:5]
                by_score = sorted(rows, key=lambda row: row["score"], reverse=True)[:5]

                snapshots.append(
                    {
                        "season_label": season_ref.label,
                        "n_titles": len(rows),
                        "sample_titles": [self._title_view(row) for row in rows[:5]],
                        "top_by_rating_total": [
                            {
                                "title": self._title_view(row),
                                "score": row["score"],
                                "rating_total": row["rating_total"],
                            }
                            for row in by_rating
                        ],
                        "top_by_score": [
                            {
                                "title": self._title_view(row),
                                "score": row["score"],
                                "rating_total": row["rating_total"],
                            }
                            for row in by_score
                        ],
                    }
                )

        return {
            "requested_seasons": [season_a_label, season_b_label],
            "page_limit": page_limit,
            "per_page": per_page,
            "min_rating_total": min_rating_total,
            "snapshots": snapshots,
        }

    async def run_prefetched_season_gap_analysis(
        self,
        *,
        season_a_label: str,
        season_b_label: str,
        page_limit: int,
        per_page: int,
        top_n: int,
        min_rating_total: int,
        output_subdir: str | None,
    ) -> SeasonGapAnalysisResponse:
        if season_a_label not in self.prefetched_rows_by_season:
            raise ValueError(
                f"No prefetched rows found for {season_a_label}. Retrieval specialist must run first."
            )
        if season_b_label not in self.prefetched_rows_by_season:
            raise ValueError(
                f"No prefetched rows found for {season_b_label}. Retrieval specialist must run first."
            )

        request = SeasonGapAnalysisRequest(
            season_a=self.parse_season_label(season_a_label),
            season_b=self.parse_season_label(season_b_label),
            page_limit=page_limit,
            per_page=per_page,
            top_n=top_n,
            min_rating_total=min_rating_total,
            output_subdir=output_subdir,
        )

        response = run_season_gap_analysis_from_prefetched_rows(
            request=request,
            settings=self.settings,
            cohort_a_rows=self.prefetched_rows_by_season[season_a_label],
            cohort_b_rows=self.prefetched_rows_by_season[season_b_label],
        )

        self.latest_analysis_response = response
        return response

    @property
    def latest_artifacts(self):
        return (
            None
            if self.latest_analysis_response is None
            else self.latest_analysis_response.artifacts
        )

    @staticmethod
    def _title_view(row: dict[str, Any]) -> str:
        name = str(row.get("name") or "").strip()
        name_cn = str(row.get("name_cn") or "").strip()
        if name_cn and name_cn != name:
            return f"{name} / {name_cn}"
        return name or name_cn
