import argparse
import asyncio

from app.analysis.season_gap import run_season_gap_analysis
from app.bangumi.client import BangumiClient
from app.core.config import get_settings
from app.schemas import SeasonGapAnalysisRequest, SeasonRef


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Bangumi seasonal gap spike.")
    parser.add_argument("--year-a", type=int, required=True)
    parser.add_argument("--season-a", type=str, required=True, choices=["winter", "spring", "summer", "fall"])
    parser.add_argument("--year-b", type=int, required=True)
    parser.add_argument("--season-b", type=str, required=True, choices=["winter", "spring", "summer", "fall"])
    parser.add_argument("--page-limit", type=int, default=4)
    parser.add_argument("--per-page", type=int, default=25)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--min-rating-total", type=int, default=30)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = get_settings()

    request = SeasonGapAnalysisRequest(
        season_a=SeasonRef(year=args.year_a, season=args.season_a),
        season_b=SeasonRef(year=args.year_b, season=args.season_b),
        page_limit=args.page_limit,
        per_page=args.per_page,
        top_n=args.top_n,
        min_rating_total=args.min_rating_total,
    )

    async with BangumiClient(settings) as client:
        response = await run_season_gap_analysis(
            client=client,
            request=request,
            settings=settings,
        )

    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
