from __future__ import annotations

import re
from typing import Literal

import pandas as pd

from app.analysis.season_gap import (
    _fetch_one_cohort,
    _record_from_row,
    compute_gap_frame,
    run_season_gap_analysis_from_prefetched_rows,
    summarize_cohort,
)
from app.bangumi.client import BangumiClient
from app.core.config import Settings
from app.schemas import (
    BangumiChatRequest,
    BangumiChatResponse,
    GapRecord,
    SeasonGapAnalysisRequest,
    SeasonRef,
)

SEASON_TOKEN_MAP = {
    "winter": "winter",
    "q1": "winter",
    "jan": "winter",
    "january": "winter",
    "1": "winter",
    "01": "winter",
    "spring": "spring",
    "q2": "spring",
    "apr": "spring",
    "april": "spring",
    "4": "spring",
    "04": "spring",
    "summer": "summer",
    "q3": "summer",
    "jul": "summer",
    "july": "summer",
    "7": "summer",
    "07": "summer",
    "fall": "fall",
    "autumn": "fall",
    "q4": "fall",
    "oct": "fall",
    "october": "fall",
    "10": "fall",
}

SEASON_TOKEN_PATTERN = (
    r"winter|spring|summer|fall|autumn|q[1-4]|january|jan|april|apr|july|jul|october|oct|10|01|04|07|1|4|7"
)

ALLOWED_TOPIC_HINTS = [
    "score",
    "scor",
    "popular",
    "rating",
    "season",
    "quarter",
    "anime",
    "title",
    "bangumi",
    "hypothesis",
    "gap",
    "compare",
    "better",
    "higher",
    "lower",
    "strongest",
    "weakest",
    "best",
    "worst",
    "hot",
    "cover",
]


def _defaults_from_current(current: SeasonGapAnalysisRequest | None) -> dict[str, int | str | None]:
    if current is None:
        return {
            "page_limit": 4,
            "per_page": 25,
            "top_n": 5,
            "min_rating_total": 30,
            "output_subdir": None,
        }
    return {
        "page_limit": current.page_limit,
        "per_page": current.per_page,
        "top_n": current.top_n,
        "min_rating_total": current.min_rating_total,
        "output_subdir": None,
    }


def _is_out_of_scope(message: str, current: SeasonGapAnalysisRequest | None) -> bool:
    lowered = message.lower()
    if current is not None:
        return False
    return not any(token in lowered for token in ALLOWED_TOPIC_HINTS)


def _normalize_token(token: str) -> str | None:
    return SEASON_TOKEN_MAP.get(token.lower())


def _extract_season_refs(message: str) -> list[SeasonRef]:
    refs: list[SeasonRef] = []
    seen: set[tuple[int, str]] = set()
    patterns = [
        rf"(?P<year>20\d{{2}})\s*[-/ ]?\s*(?P<token>{SEASON_TOKEN_PATTERN})",
        rf"(?P<token>{SEASON_TOKEN_PATTERN})\s*[-/ ]?\s*(?P<year>20\d{{2}})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, message, flags=re.IGNORECASE):
            year = int(match.group("year"))
            token = _normalize_token(match.group("token"))
            if token is None:
                continue
            key = (year, token)
            if key in seen:
                continue
            seen.add(key)
            refs.append(SeasonRef(year=year, season=token))
    return refs


def _extract_target_year(message: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", message)
    if not match:
        return None
    return int(match.group(1))


def _is_year_level_season_question(message: str) -> bool:
    lowered = message.lower()
    if _extract_target_year(lowered) is None:
        return False
    return any(token in lowered for token in ["season", "quarter"])


def _is_year_level_title_question(message: str) -> bool:
    lowered = message.lower()
    if _extract_target_year(lowered) is None:
        return False
    if any(token in lowered for token in ["anime", "title", "titles", "shows", "show"]):
        return len(_extract_season_refs(lowered)) == 0
    return False


def _detect_intent(message: str) -> str:
    lowered = message.lower()

    if _is_year_level_season_question(lowered):
        if any(
            phrase in lowered
            for phrase in [
                "more popular",
                "most popular",
                "popular",
                "popularity",
                "rating total",
                "highest rating total",
                "hotter",
            ]
        ):
            return "rank_year_popularity"

        if any(
            phrase in lowered
            for phrase in [
                "average score",
                "higher average score",
                "highest average score",
                "higher score",
                "score",
                "best",
                "strongest",
                "highest",
                "better received",
                "higher rated",
            ]
        ):
            return "rank_year_score"

    if _is_year_level_title_question(lowered):
        if any(
            phrase in lowered
            for phrase in [
                "most popular anime",
                "most popular titles",
                "most popular shows",
                "popular anime",
                "popular titles",
                "highest rating total",
            ]
        ):
            return "year_top_popularity_titles"

        if any(
            phrase in lowered
            for phrase in [
                "top rated anime",
                "top rated titles",
                "highest rated anime",
                "highest rated titles",
                "best anime",
                "best titles",
                "top anime",
                "top titles",
            ]
        ):
            return "year_top_score_titles"

    if any(word in lowered for word in ["top positive gap", "positive gap", "underrated"]):
        return "top_positive_gap"

    if any(word in lowered for word in ["top negative gap", "negative gap", "overrated"]):
        return "top_negative_gap"

    if any(word in lowered for word in ["highest rated", "best anime", "best title", "top anime", "top titles", "top rated anime"]):
        return "top_score_titles"

    if any(word in lowered for word in ["most popular titles", "most popular anime", "hottest", "highest rating total"]):
        return "top_popularity_titles"

    if any(word in lowered for word in ["hypothesis", "takeaway", "conclusion"]):
        return "hypothesis"

    if any(word in lowered for word in ["how many titles", "more titles", "fewer titles", "number of titles"]):
        return "titles"

    if any(word in lowered for word in ["popular", "popularity", "rating total", "hotter"]):
        return "compare_popularity"

    if any(word in lowered for word in ["score", "better received", "higher rated", "higher score"]):
        return "compare_score"

    return "compare_overview"


async def _run_pair_analysis_with_frame(
    request: SeasonGapAnalysisRequest,
    settings: Settings,
) -> tuple:
    async with BangumiClient(settings) as client:
        cohort_a_raw = await _fetch_one_cohort(client, request.season_a, request)
        cohort_b_raw = await _fetch_one_cohort(client, request.season_b, request)

    response = run_season_gap_analysis_from_prefetched_rows(
        request=request,
        settings=settings,
        cohort_a_rows=cohort_a_raw,
        cohort_b_rows=cohort_b_raw,
    )
    combined = compute_gap_frame(pd.concat([cohort_a_raw, cohort_b_raw], ignore_index=True))
    return response, combined


async def _run_single_season_frame(
    season_ref: SeasonRef,
    current: SeasonGapAnalysisRequest | None,
    settings: Settings,
) -> pd.DataFrame:
    defaults = _defaults_from_current(current)
    dummy_request = SeasonGapAnalysisRequest(
        season_a=season_ref,
        season_b=season_ref,
        page_limit=int(defaults["page_limit"]),
        per_page=int(defaults["per_page"]),
        top_n=int(defaults["top_n"]),
        min_rating_total=int(defaults["min_rating_total"]),
        output_subdir=None,
    )
    async with BangumiClient(settings) as client:
        cohort_raw = await _fetch_one_cohort(client, season_ref, dummy_request)
    return compute_gap_frame(cohort_raw)


def _frame_to_summary(frame: pd.DataFrame, label: str):
    return summarize_cohort(frame, season_label=label, top_n=3)


async def _collect_year_frames(
    year: int,
    current: SeasonGapAnalysisRequest | None,
    settings: Settings,
) -> tuple[dict[str, pd.DataFrame], list]:
    frames_by_label: dict[str, pd.DataFrame] = {}
    summaries = []
    for season in ["winter", "spring", "summer", "fall"]:
        season_ref = SeasonRef(year=year, season=season)
        frame = await _run_single_season_frame(season_ref, current, settings)
        if frame.empty:
            continue
        frames_by_label[season_ref.label] = frame
        summaries.append(_frame_to_summary(frame, season_ref.label))
    return frames_by_label, summaries


async def _run_year_rankings(
    year: int,
    metric: Literal["score", "popularity"],
    current: SeasonGapAnalysisRequest | None,
    settings: Settings,
) -> BangumiChatResponse:
    frames_by_label, summaries = await _collect_year_frames(year, current, settings)

    if not summaries:
        return BangumiChatResponse(
            question=f"{year} ranking",
            answer=f"I could not retrieve enough Bangumi rows to rank the {year} seasons.",
            out_of_scope=False,
        )

    if metric == "score":
        ranked = sorted(summaries, key=lambda x: x.avg_score, reverse=True)
        evidence = [f"{item.season_label}: average score {item.avg_score:.2f}" for item in ranked]
        answer = (
            f"Within {year}, {ranked[0].season_label} had the highest average score "
            f"at {ranked[0].avg_score:.2f}."
        )
        winner_frame = frames_by_label.get(ranked[0].season_label, pd.DataFrame())
        suggested = _select_top_titles(winner_frame, season_label=None, sort_by="score")
    else:
        ranked = sorted(summaries, key=lambda x: x.avg_rating_total, reverse=True)
        evidence = [f"{item.season_label}: average rating total {item.avg_rating_total:.2f}" for item in ranked]
        answer = (
            f"Within {year}, {ranked[0].season_label} was the most popular season by the rating-total proxy "
            f"at {ranked[0].avg_rating_total:.2f}."
        )
        winner_frame = frames_by_label.get(ranked[0].season_label, pd.DataFrame())
        suggested = _select_top_titles(winner_frame, season_label=None, sort_by="rating_total")

    return BangumiChatResponse(
        question=f"Which {year} season ranked highest by {metric}?",
        answer=answer,
        pair_used=[item.season_label for item in ranked],
        evidence=evidence,
        suggested_titles=suggested,
    )


async def _run_year_top_titles(
    year: int,
    metric: Literal["score", "popularity"],
    current: SeasonGapAnalysisRequest | None,
    settings: Settings,
) -> BangumiChatResponse:
    frames_by_label, summaries = await _collect_year_frames(year, current, settings)

    if not frames_by_label:
        return BangumiChatResponse(
            question=f"{year} top titles",
            answer=f"I could not retrieve enough Bangumi rows for {year}.",
        )

    combined = pd.concat(list(frames_by_label.values()), ignore_index=True)
    combined = combined.sort_values(["score", "rating_total"], ascending=[False, False]).drop_duplicates(subset=["subject_id"])
    if metric == "score":
        titles = _select_top_titles(combined, season_label=None, sort_by="score", top_n=5)
        answer = f"Here are the top rated anime I found across the {year} seasonal windows."
        evidence = [
            f"{title.name_cn or title.name}: {title.season_label}, score {title.score:.2f}, rating total {title.rating_total}"
            for title in titles
        ]
    else:
        titles = _select_top_titles(combined, season_label=None, sort_by="rating_total", top_n=5)
        answer = f"Here are the most popular anime I found across the {year} seasonal windows by the rating-total proxy."
        evidence = [
            f"{title.name_cn or title.name}: {title.season_label}, rating total {title.rating_total}, score {title.score:.2f}"
            for title in titles
        ]

    return BangumiChatResponse(
        question=f"{year} top titles by {metric}",
        answer=answer,
        pair_used=[item.season_label for item in summaries],
        evidence=evidence,
        suggested_titles=titles,
    )


def _select_top_titles(df: pd.DataFrame, *, season_label: str | None, sort_by: str, top_n: int = 3) -> list[GapRecord]:
    work = df.copy()
    if season_label is not None:
        work = work[work["season_label"] == season_label].copy()
    if work.empty:
        return []
    secondary = "rating_total" if sort_by == "score" else "score"
    selected = work.sort_values([sort_by, secondary], ascending=[False, False]).head(top_n)
    return [_record_from_row(row) for _, row in selected.iterrows()]


def _build_pair_request(
    refs: list[SeasonRef],
    current: SeasonGapAnalysisRequest | None,
) -> SeasonGapAnalysisRequest | None:
    defaults = _defaults_from_current(current)
    if len(refs) >= 2:
        return SeasonGapAnalysisRequest(
            season_a=refs[0],
            season_b=refs[1],
            page_limit=int(defaults["page_limit"]),
            per_page=int(defaults["per_page"]),
            top_n=int(defaults["top_n"]),
            min_rating_total=int(defaults["min_rating_total"]),
            output_subdir=None,
        )
    return current


def _response_from_out_of_scope(message: str) -> BangumiChatResponse:
    return BangumiChatResponse(
        question=message,
        answer=(
            "I can answer Bangumi seasonal analysis questions in English, such as score, popularity, "
            "title counts, gap titles, hypotheses, year-level season comparisons, and top anime by score or popularity."
        ),
        out_of_scope=True,
    )


async def answer_bangumi_question(
    request: BangumiChatRequest,
    settings: Settings,
) -> BangumiChatResponse:
    message = request.message.strip()
    if _is_out_of_scope(message, request.current_request):
        return _response_from_out_of_scope(message)

    refs = _extract_season_refs(message)
    intent = _detect_intent(message)
    lowered = message.lower()

    if intent in {"rank_year_popularity", "rank_year_score"}:
        year = _extract_target_year(lowered)
        if year is not None:
            metric = "popularity" if intent == "rank_year_popularity" else "score"
            return await _run_year_rankings(year, metric, request.current_request, settings)

    if intent in {"year_top_score_titles", "year_top_popularity_titles"}:
        year = _extract_target_year(lowered)
        if year is not None:
            metric = "score" if intent == "year_top_score_titles" else "popularity"
            return await _run_year_top_titles(year, metric, request.current_request, settings)

    if intent in {"top_score_titles", "top_popularity_titles"} and len(refs) == 1:
        frame = await _run_single_season_frame(refs[0], request.current_request, settings)
        if frame.empty:
            return BangumiChatResponse(
                question=message,
                answer=f"I could not retrieve enough data for {refs[0].label}.",
            )
        sort_by = "score" if intent == "top_score_titles" else "rating_total"
        cards = _select_top_titles(frame, season_label=refs[0].label, sort_by=sort_by, top_n=5)
        metric_label = "score" if intent == "top_score_titles" else "rating total"
        answer = f"Here are the top {len(cards)} {refs[0].label} titles by {metric_label}."
        evidence = [
            f"{title.name_cn or title.name}: score {title.score:.2f}, rating total {title.rating_total}"
            for title in cards
        ]
        return BangumiChatResponse(
            question=message,
            answer=answer,
            pair_used=[refs[0].label],
            evidence=evidence,
            suggested_titles=cards,
        )

    pair_request = _build_pair_request(refs, request.current_request)
    if pair_request is None:
        return BangumiChatResponse(
            question=message,
            answer=(
                "Please specify two seasons, for example 'Compare 2025 spring and 2025 summer', "
                "or ask a year-level question such as 'Which season was more popular in 2012?' "
                "or 'What are the top rated anime in 2024?'"
            ),
            out_of_scope=False,
        )

    response, combined = await _run_pair_analysis_with_frame(pair_request, settings)
    cohorts = {item.season_label: item for item in response.cohorts}
    season_a = pair_request.season_a.label
    season_b = pair_request.season_b.label
    summary_a = cohorts.get(season_a)
    summary_b = cohorts.get(season_b)

    if summary_a is None or summary_b is None:
        return BangumiChatResponse(
            question=message,
            answer="I could not produce a comparison summary for the requested seasons.",
        )

    if intent == "compare_score":
        winner = season_a if summary_a.avg_score >= summary_b.avg_score else season_b
        win_score = summary_a.avg_score if winner == season_a else summary_b.avg_score
        lose_score = summary_b.avg_score if winner == season_a else summary_a.avg_score
        suggested = _select_top_titles(combined, season_label=winner, sort_by="score", top_n=5)
        return BangumiChatResponse(
            question=message,
            answer=(
                f"{winner} had the higher average score: {win_score:.2f} versus {lose_score:.2f}."
            ),
            pair_used=[season_a, season_b],
            evidence=[
                f"{season_a}: average score {summary_a.avg_score:.2f}",
                f"{season_b}: average score {summary_b.avg_score:.2f}",
            ],
            suggested_titles=suggested,
        )

    if intent == "compare_popularity":
        winner = season_a if summary_a.avg_rating_total >= summary_b.avg_rating_total else season_b
        win_pop = summary_a.avg_rating_total if winner == season_a else summary_b.avg_rating_total
        lose_pop = summary_b.avg_rating_total if winner == season_a else summary_a.avg_rating_total
        suggested = _select_top_titles(combined, season_label=winner, sort_by="rating_total", top_n=5)
        return BangumiChatResponse(
            question=message,
            answer=(
                f"{winner} was more popular by the rating-total proxy: {win_pop:.2f} versus {lose_pop:.2f}."
            ),
            pair_used=[season_a, season_b],
            evidence=[
                f"{season_a}: average rating total {summary_a.avg_rating_total:.2f}",
                f"{season_b}: average rating total {summary_b.avg_rating_total:.2f}",
            ],
            suggested_titles=suggested,
        )

    if intent == "titles":
        winner = season_a if summary_a.n_titles >= summary_b.n_titles else season_b
        return BangumiChatResponse(
            question=message,
            answer=f"{winner} had more titles: {summary_a.n_titles} versus {summary_b.n_titles}."
            if winner == season_a
            else f"{winner} had more titles: {summary_b.n_titles} versus {summary_a.n_titles}.",
            pair_used=[season_a, season_b],
            evidence=[
                f"{season_a}: {summary_a.n_titles} titles",
                f"{season_b}: {summary_b.n_titles} titles",
            ],
        )

    if intent == "top_positive_gap":
        cards = summary_a.top_positive_gap_titles[:2] + summary_b.top_positive_gap_titles[:2]
        return BangumiChatResponse(
            question=message,
            answer="These are the strongest positive-gap titles from the selected comparison.",
            pair_used=[season_a, season_b],
            evidence=[
                f"{title.name_cn or title.name}: gap {title.gap:.2f}, score {title.score:.2f}, rating total {title.rating_total}"
                for title in cards
            ],
            suggested_titles=cards,
        )

    if intent == "top_negative_gap":
        cards = summary_a.top_negative_gap_titles[:2] + summary_b.top_negative_gap_titles[:2]
        return BangumiChatResponse(
            question=message,
            answer="These are the strongest negative-gap titles from the selected comparison.",
            pair_used=[season_a, season_b],
            evidence=[
                f"{title.name_cn or title.name}: gap {title.gap:.2f}, score {title.score:.2f}, rating total {title.rating_total}"
                for title in cards
            ],
            suggested_titles=cards,
        )

    if intent == "top_score_titles":
        cards = _select_top_titles(combined, season_label=None, sort_by="score", top_n=5)
        return BangumiChatResponse(
            question=message,
            answer="Here are the highest-rated titles in the current comparison.",
            pair_used=[season_a, season_b],
            evidence=[
                f"{title.name_cn or title.name}: score {title.score:.2f}, rating total {title.rating_total}"
                for title in cards
            ],
            suggested_titles=cards,
        )

    if intent == "top_popularity_titles":
        cards = _select_top_titles(combined, season_label=None, sort_by="rating_total", top_n=5)
        return BangumiChatResponse(
            question=message,
            answer="Here are the most popular titles in the current comparison by rating-total volume.",
            pair_used=[season_a, season_b],
            evidence=[
                f"{title.name_cn or title.name}: rating total {title.rating_total}, score {title.score:.2f}"
                for title in cards
            ],
            suggested_titles=cards,
        )

    if intent == "hypothesis":
        largest = response.comparison.largest_gap_title
        suggested = [largest] if largest is not None else []
        evidence = [
            f"Higher scoring season: {response.comparison.higher_scoring_season or 'tie'}",
            f"Higher popularity season: {response.comparison.higher_popularity_season or 'tie'}",
        ]
        return BangumiChatResponse(
            question=message,
            answer=response.comparison.hypothesis,
            pair_used=[season_a, season_b],
            evidence=evidence,
            suggested_titles=suggested,
        )

    winner_score = response.comparison.higher_scoring_season or "Neither season"
    winner_popularity = response.comparison.higher_popularity_season or "Neither season"
    suggested = _select_top_titles(
        combined,
        season_label=response.comparison.higher_scoring_season,
        sort_by="score",
        top_n=5,
    )
    return BangumiChatResponse(
        question=message,
        answer=(
            f"For {season_a} versus {season_b}, {winner_score} had the higher average score and "
            f"{winner_popularity} had the higher popularity proxy."
        ),
        pair_used=[season_a, season_b],
        evidence=[
            f"{season_a}: average score {summary_a.avg_score:.2f}, average rating total {summary_a.avg_rating_total:.2f}",
            f"{season_b}: average score {summary_b.avg_score:.2f}, average rating total {summary_b.avg_rating_total:.2f}",
            f"Hypothesis: {response.comparison.hypothesis}",
        ],
        suggested_titles=suggested,
    )
