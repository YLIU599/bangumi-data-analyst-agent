import pandas as pd

from app.analysis.season_gap import compute_gap_frame, season_to_date_bounds
from app.schemas import SeasonRef


def test_season_to_date_bounds_spring():
    start_date, end_date = season_to_date_bounds(SeasonRef(year=2024, season="spring"))
    assert str(start_date) == "2024-04-01"
    assert str(end_date) == "2024-07-01"


def test_season_to_date_bounds_fall():
    start_date, end_date = season_to_date_bounds(SeasonRef(year=2024, season="fall"))
    assert str(start_date) == "2024-10-01"
    assert str(end_date) == "2025-01-01"


def test_compute_gap_frame_adds_expected_columns():
    df = pd.DataFrame(
        [
            {"subject_id": 1, "name": "A", "season_label": "2024-spring", "score": 8.5, "rating_total": 120},
            {"subject_id": 2, "name": "B", "season_label": "2024-spring", "score": 7.0, "rating_total": 800},
            {"subject_id": 3, "name": "C", "season_label": "2024-summer", "score": 8.2, "rating_total": 200},
        ]
    )

    result = compute_gap_frame(df)

    assert "popularity_log10" in result.columns
    assert "score_z" in result.columns
    assert "popularity_z" in result.columns
    assert "gap" in result.columns
    assert len(result) == 3
