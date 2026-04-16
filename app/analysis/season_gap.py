from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any

import numpy as np
import pandas as pd

from app.artifacts.files import create_run_dir, write_dataframe_csv, write_json_file
from app.artifacts.plotting import save_gap_scatter_plot
from app.bangumi.client import BangumiClient
from app.core.config import Settings
from app.schemas import (
    ArtifactPaths,
    CohortSummary,
    ComparisonSummary,
    GapRecord,
    SeasonGapAnalysisRequest,
    SeasonGapAnalysisResponse,
    SeasonRef,
)


def season_to_date_bounds(season_ref: SeasonRef) -> tuple[date, date]:
    year = season_ref.year
    season = season_ref.season

    if season == "winter":
        return date(year, 1, 1), date(year, 4, 1)
    if season == "spring":
        return date(year, 4, 1), date(year, 7, 1)
    if season == "summer":
        return date(year, 7, 1), date(year, 10, 1)
    return date(year, 10, 1), date(year + 1, 1, 1)


def season_to_start_month(season_ref: SeasonRef) -> int:
    if season_ref.season == "winter":
        return 1
    if season_ref.season == "spring":
        return 4
    if season_ref.season == "summer":
        return 7
    return 10


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_subject(raw: dict[str, Any], season_label: str) -> dict[str, Any] | None:
    rating = raw.get("rating") or {}
    collection = raw.get("collection") or {}

    score = _safe_float(rating.get("score"))
    rating_total = _safe_int(rating.get("total"))

    collection_total = _safe_int(collection.get("total"))
    collection_wish = _safe_int(collection.get("wish"))
    collection_doing = _safe_int(collection.get("doing") or collection.get("do"))
    collection_done = _safe_int(collection.get("done"))
    collection_on_hold = _safe_int(collection.get("on_hold"))
    collection_dropped = _safe_int(collection.get("dropped"))

    if rating_total <= 0 and collection_total > 0:
        rating_total = collection_total

    item_date = raw.get("date") or raw.get("air_date")

    if score is None:
        return None
    if rating_total <= 0:
        return None
    if not item_date:
        return None

    return {
        "subject_id": _safe_int(raw.get("id")),
        "name": (raw.get("name") or "").strip(),
        "name_cn": (raw.get("name_cn") or "").strip() or None,
        "season_label": season_label,
        "air_date": item_date,
        "score": score,
        "rating_total": rating_total,
        "rank": _safe_int(raw.get("rank")),
        "collection_total": collection_total,
        "collection_wish": collection_wish,
        "collection_doing": collection_doing,
        "collection_done": collection_done,
        "collection_on_hold": collection_on_hold,
        "collection_dropped": collection_dropped,
    }


def rows_to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "subject_id",
                "name",
                "name_cn",
                "season_label",
                "air_date",
                "score",
                "rating_total",
                "rank",
                "collection_total",
                "collection_wish",
                "collection_doing",
                "collection_done",
                "collection_on_hold",
                "collection_dropped",
            ]
        )

    df = pd.DataFrame(rows).drop_duplicates(subset=["subject_id"])
    df["popularity_log10"] = np.log10(df["rating_total"] + 1)

    score_std = float(df["score"].std(ddof=0)) if len(df) > 1 else 0.0
    pop_std = float(df["popularity_log10"].std(ddof=0)) if len(df) > 1 else 0.0

    df["score_z"] = 0.0 if score_std == 0 else (df["score"] - df["score"].mean()) / score_std
    df["popularity_z"] = (
        0.0
        if pop_std == 0
        else (df["popularity_log10"] - df["popularity_log10"].mean()) / pop_std
    )
    df["gap"] = df["score_z"] - df["popularity_z"]
    return df.sort_values(["season_label", "gap"], ascending=[True, False]).reset_index(drop=True)


def compute_gap_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work = df.copy()
    work["popularity_log10"] = np.log10(work["rating_total"] + 1)

    score_std = float(work["score"].std(ddof=0)) if len(work) > 1 else 0.0
    pop_std = float(work["popularity_log10"].std(ddof=0)) if len(work) > 1 else 0.0

    work["score_z"] = 0.0 if score_std == 0 else (work["score"] - work["score"].mean()) / score_std
    work["popularity_z"] = (
        0.0
        if pop_std == 0
        else (work["popularity_log10"] - work["popularity_log10"].mean()) / pop_std
    )
    work["gap"] = work["score_z"] - work["popularity_z"]
    return work


def _record_from_row(row: pd.Series) -> GapRecord:
    return GapRecord(
        subject_id=int(row["subject_id"]),
        name=str(row["name"]),
        name_cn=None if pd.isna(row.get("name_cn")) else str(row["name_cn"]),
        season_label=str(row["season_label"]),
        air_date=None if pd.isna(row.get("air_date")) else str(row["air_date"]),
        score=float(row["score"]),
        rating_total=int(row["rating_total"]),
        popularity_log10=float(row["popularity_log10"]),
        gap=float(row["gap"]),
    )


def summarize_cohort(df: pd.DataFrame, *, season_label: str, top_n: int) -> CohortSummary:
    if df.empty:
        return CohortSummary(
            season_label=season_label,
            n_titles=0,
            avg_score=0.0,
            avg_rating_total=0.0,
            avg_gap=0.0,
            median_gap=0.0,
            top_positive_gap_titles=[],
            top_negative_gap_titles=[],
        )

    positive = df.sort_values("gap", ascending=False).head(top_n)
    negative = df.sort_values("gap", ascending=True).head(top_n)

    return CohortSummary(
        season_label=season_label,
        n_titles=int(len(df)),
        avg_score=round(float(df["score"].mean()), 4),
        avg_rating_total=round(float(df["rating_total"].mean()), 4),
        avg_gap=round(float(df["gap"].mean()), 4),
        median_gap=round(float(median(df["gap"].tolist())), 4),
        top_positive_gap_titles=[_record_from_row(row) for _, row in positive.iterrows()],
        top_negative_gap_titles=[_record_from_row(row) for _, row in negative.iterrows()],
    )


def build_hypothesis(summary_a: CohortSummary, summary_b: CohortSummary, largest_gap: GapRecord | None) -> str:
    if summary_a.n_titles == 0 or summary_b.n_titles == 0:
        return "Insufficient data to form a seasonal hypothesis."

    score_diff = round(summary_a.avg_score - summary_b.avg_score, 3)
    pop_diff = round(summary_a.avg_rating_total - summary_b.avg_rating_total, 3)

    if abs(score_diff) > 0.15 and abs(pop_diff) > 50:
        direction_score = summary_a.season_label if score_diff > 0 else summary_b.season_label
        direction_pop = summary_a.season_label if pop_diff > 0 else summary_b.season_label
        if direction_score != direction_pop:
            base = (
                f"Preliminary hypothesis: audience size and audience reception diverge across these two "
                f"cohorts. {direction_score} has the stronger average score, while {direction_pop} has the "
                f"larger average rating volume."
            )
        else:
            base = (
                f"Preliminary hypothesis: {direction_score} may have been both better received and more "
                f"widely watched than the comparison cohort."
            )
    else:
        base = (
            "Preliminary hypothesis: the two cohorts look broadly similar at the aggregate level, so the "
            "more informative signal is title-level dispersion rather than season-level averages."
        )

    if largest_gap is not None:
        return (
            f"{base} The strongest title-level discrepancy is {largest_gap.name}"
            f"{' / ' + largest_gap.name_cn if largest_gap.name_cn else ''}, which has a gap score of "
            f"{largest_gap.gap:.3f}."
        )

    return base


def _coerce_prefetched_rows_to_frame(
    rows_or_frame: list[dict[str, Any]] | pd.DataFrame,
) -> pd.DataFrame:
    if isinstance(rows_or_frame, pd.DataFrame):
        return rows_or_frame.copy()

    if not rows_or_frame:
        return pd.DataFrame()

    return pd.DataFrame(rows_or_frame)


def _build_response_from_cohort_frames(
    *,
    cohort_a_raw: pd.DataFrame,
    cohort_b_raw: pd.DataFrame,
    request: SeasonGapAnalysisRequest,
    settings: Settings,
) -> SeasonGapAnalysisResponse:
    combined_raw = pd.concat([cohort_a_raw, cohort_b_raw], ignore_index=True)
    if combined_raw.empty:
        raise ValueError("No Bangumi rows matched the request after normalization and filtering.")

    combined = compute_gap_frame(combined_raw)

    cohort_a = combined[combined["season_label"] == request.season_a.label].copy()
    cohort_b = combined[combined["season_label"] == request.season_b.label].copy()

    summary_a = summarize_cohort(cohort_a, season_label=request.season_a.label, top_n=request.top_n)
    summary_b = summarize_cohort(cohort_b, season_label=request.season_b.label, top_n=request.top_n)

    largest_gap_row = (
        combined.iloc[combined["gap"].abs().idxmax()] if not combined.empty else None
    )
    largest_gap = _record_from_row(largest_gap_row) if largest_gap_row is not None else None

    comparison = ComparisonSummary(
        higher_scoring_season=(
            request.season_a.label
            if summary_a.avg_score > summary_b.avg_score
            else request.season_b.label
            if summary_b.avg_score > summary_a.avg_score
            else None
        ),
        higher_popularity_season=(
            request.season_a.label
            if summary_a.avg_rating_total > summary_b.avg_rating_total
            else request.season_b.label
            if summary_b.avg_rating_total > summary_a.avg_rating_total
            else None
        ),
        largest_gap_title=largest_gap,
        hypothesis=build_hypothesis(summary_a, summary_b, largest_gap),
    )

    run_dir = create_run_dir(
        settings=settings,
        season_a=request.season_a.label,
        season_b=request.season_b.label,
        output_subdir=request.output_subdir,
    )

    combined_csv = write_dataframe_csv(combined, run_dir / "combined_cohorts.csv")
    summary_payload = {
        "request": request.model_dump(),
        "combined_n_titles": int(len(combined)),
        "cohorts": [summary_a.model_dump(), summary_b.model_dump()],
        "comparison": comparison.model_dump(),
    }
    summary_json = write_json_file(summary_payload, run_dir / "summary.json")
    scatter_plot_png = save_gap_scatter_plot(combined, run_dir / "score_vs_popularity.png")

    return SeasonGapAnalysisResponse(
        request=request,
        combined_n_titles=int(len(combined)),
        cohorts=[summary_a, summary_b],
        comparison=comparison,
        artifacts=ArtifactPaths(
            run_dir=str(run_dir),
            combined_csv=str(combined_csv),
            summary_json=str(summary_json),
            scatter_plot_png=str(scatter_plot_png),
        ),
    )


def run_season_gap_analysis_from_prefetched_rows(
    *,
    request: SeasonGapAnalysisRequest,
    settings: Settings,
    cohort_a_rows: list[dict[str, Any]] | pd.DataFrame,
    cohort_b_rows: list[dict[str, Any]] | pd.DataFrame,
) -> SeasonGapAnalysisResponse:
    cohort_a_raw = _coerce_prefetched_rows_to_frame(cohort_a_rows)
    cohort_b_raw = _coerce_prefetched_rows_to_frame(cohort_b_rows)

    return _build_response_from_cohort_frames(
        cohort_a_raw=cohort_a_raw,
        cohort_b_raw=cohort_b_raw,
        request=request,
        settings=settings,
    )


async def _fetch_one_cohort(
    client: BangumiClient,
    season_ref: SeasonRef,
    request: SeasonGapAnalysisRequest,
) -> pd.DataFrame:
    month = season_to_start_month(season_ref)
    raw_items = await client.fetch_season_subjects(
        year=season_ref.year,
        month=month,
        page_limit=request.page_limit,
        per_page=request.per_page,
    )

    rows: list[dict[str, Any]] = []
    for item in raw_items:
        normalized = normalize_subject(item, season_ref.label)
        if normalized is None:
            continue
        if normalized["rating_total"] < request.min_rating_total:
            continue
        rows.append(normalized)

    return pd.DataFrame(rows)


async def run_season_gap_analysis(
    *,
    client: BangumiClient,
    request: SeasonGapAnalysisRequest,
    settings: Settings,
) -> SeasonGapAnalysisResponse:
    cohort_a_raw = await _fetch_one_cohort(client, request.season_a, request)
    cohort_b_raw = await _fetch_one_cohort(client, request.season_b, request)

    return run_season_gap_analysis_from_prefetched_rows(
        request=request,
        settings=settings,
        cohort_a_rows=cohort_a_raw,
        cohort_b_rows=cohort_b_raw,
    )
