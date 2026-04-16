from __future__ import annotations

import json

from agents import RunContextWrapper, function_tool

from app.agents.backend import AgentWorkflowBackend


@function_tool(failure_error_function=None)
async def fetch_runtime_bangumi_snapshots(
    ctx: RunContextWrapper[AgentWorkflowBackend],
    season_a_label: str,
    season_b_label: str,
    page_limit: int,
    per_page: int,
    min_rating_total: int,
) -> str:
    """Fetch compact runtime Bangumi season snapshots for two seasonal cohorts."""
    payload = await ctx.context.fetch_runtime_season_snapshots(
        season_a_label=season_a_label,
        season_b_label=season_b_label,
        page_limit=page_limit,
        per_page=per_page,
        min_rating_total=min_rating_total,
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


@function_tool(failure_error_function=None)
async def run_existing_season_gap_analysis_tool(
    ctx: RunContextWrapper[AgentWorkflowBackend],
    season_a_label: str,
    season_b_label: str,
    page_limit: int,
    per_page: int,
    top_n: int,
    min_rating_total: int,
    output_subdir: str | None = None,
) -> str:
    """Analyze already-prefetched cohort rows with the existing season-gap analysis logic."""
    response = await ctx.context.run_prefetched_season_gap_analysis(
        season_a_label=season_a_label,
        season_b_label=season_b_label,
        page_limit=page_limit,
        per_page=per_page,
        top_n=top_n,
        min_rating_total=min_rating_total,
        output_subdir=output_subdir,
    )
    payload = {
        "combined_n_titles": response.combined_n_titles,
        "cohorts": [cohort.model_dump() for cohort in response.cohorts],
        "comparison": response.comparison.model_dump(),
        "artifacts": response.artifacts.model_dump(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
