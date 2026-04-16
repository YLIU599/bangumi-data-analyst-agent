from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


def _configure_cjk_font_fallback() -> None:
    preferred_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Microsoft JhengHei",
        "Yu Gothic",
        "MS Gothic",
        "Meiryo",
        "Noto Sans CJK JP",
    ]
    available_fonts = {font.name for font in fm.fontManager.ttflist}

    chosen_font = next((font for font in preferred_fonts if font in available_fonts), None)
    if chosen_font is not None:
        plt.rcParams["font.sans-serif"] = [chosen_font, "DejaVu Sans", "sans-serif"]

    plt.rcParams["axes.unicode_minus"] = False


def save_gap_scatter_plot(df: pd.DataFrame, path: Path, annotate_n: int = 5) -> Path:
    _configure_cjk_font_fallback()
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7))

    for season_label, part in df.groupby("season_label"):
        ax.scatter(
            part["popularity_log10"],
            part["score"],
            alpha=0.75,
            label=season_label,
        )

    candidates = df.reindex(df["gap"].abs().sort_values(ascending=False).index).head(annotate_n)
    for _, row in candidates.iterrows():
        label = row["name"]
        if pd.notna(row.get("name_cn")) and row["name_cn"]:
            label = row["name_cn"]
        ax.annotate(
            label,
            (row["popularity_log10"], row["score"]),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points",
        )

    ax.set_xlabel("log10(rating_total + 1)")
    ax.set_ylabel("score")
    ax.set_title("Bangumi seasonal cohort: score vs popularity")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
