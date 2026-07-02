#!/usr/bin/env python3
"""Plot TCAM occupancy (SFT size) vs idle timeout: box plot + delay gap."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

# Switch mean packet-processing delay E[D] (s) from analytical model (Δ = idle timeout).
MEAN_DELAY_S: dict[int, float] = {
    1: 1.13,
    2: 0.71,
    3: 0.57,
    4: 0.53,
    5: 0.51,
    10: 0.50,
}

IDLE_TIMEOUTS = [1, 2, 3, 4, 5, 10]
OPTIMAL_MEAN_DELAY_S = 0.50
OPTIMAL_IDLE_TIMEOUT_S = 10
OCCUPANCY_SCALE = 100  # display occupancy in units of 100 flows
OCCUPANCY_YLABEL = r"TCAM Occupancy ($\times 10^{2}$ Flows)"
OCCUPANCY_FILL = "#3B9DFF"
OCCUPANCY_EDGE = "#0066CC"
OCCUPANCY_AXIS_COLOR = "#0066CC"
DELAY_YLABEL = r"$(E[D]-E[D]^*)/E[D]^* \times 100$ (%)"
DELAY_COLOR = "#E41A1C"
DELAY_AXIS_COLOR = "#E41A1C"
FONT_TITLE = 14
FONT_LABEL = 14
FONT_TICK = 13
OCCUPANCY_TICK_STEP = 5
DELAY_GAP_TICK_STEP = 25  # 5× occupancy step so ticks align (25 ↔ 125%)
DELAY_GAP_AXIS_RATIO = DELAY_GAP_TICK_STEP / OCCUPANCY_TICK_STEP
FONT_LEGEND = 14


def paired_axis_limits(data_peak: float, delay_gap_peak: float) -> tuple[float, float]:
    """Pick shared 0–top limits so left/right tick marks line up (25 ↔ 125%, etc.)."""
    occ_ymax = float(
        np.ceil(max(data_peak, delay_gap_peak / DELAY_GAP_AXIS_RATIO) / OCCUPANCY_TICK_STEP)
        * OCCUPANCY_TICK_STEP
    )
    gap_ymax = occ_ymax * DELAY_GAP_AXIS_RATIO
    return occ_ymax, gap_ymax


def style_occupancy_yaxis(ax, ymax: float) -> None:
    ax.set_ylabel(OCCUPANCY_YLABEL, fontsize=FONT_LABEL, color=OCCUPANCY_AXIS_COLOR)
    ax.tick_params(axis="y", labelsize=FONT_TICK, colors=OCCUPANCY_AXIS_COLOR)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_major_locator(MultipleLocator(OCCUPANCY_TICK_STEP))


def style_delay_gap_yaxis(ax, ymax: float) -> None:
    ax.set_ylabel(DELAY_YLABEL, fontsize=FONT_LABEL, color=DELAY_AXIS_COLOR, labelpad=2)
    ax.tick_params(axis="y", labelsize=FONT_TICK, colors=DELAY_AXIS_COLOR, pad=1)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_major_locator(MultipleLocator(DELAY_GAP_TICK_STEP))


def gap_to_optimal_delay_pct(delay_s: float) -> float:
    """(E[D] - E[D]*) / E[D]* × 100%; 0% at optimal."""
    return 100.0 * (delay_s - OPTIMAL_MEAN_DELAY_S) / OPTIMAL_MEAN_DELAY_S


def load_sft_sizes(csv_path: Path) -> list[int]:
    sizes: list[int] = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith("#") or row[0] == "time_s":
                continue
            sizes.append(int(row[1]))
    return sizes


def load_trace_data(raw_dir: Path, stem: str) -> dict[int, list[int]]:
    data: dict[int, list[int]] = {}
    for t in IDLE_TIMEOUTS:
        path = raw_dir / f"{stem}_sft_idle{t}s_int1s.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing simulation CSV: {path}")
        data[t] = load_sft_sizes(path)
    return data


def plot_comparison(
    data: dict[int, list[int]],
    output_path: Path,
    *,
    trace_label: str = "trace_1",
) -> None:
    # Single-column width (~3.5 in).
    fig_w, fig_h = 5.5, 3.5
    fig, ax_box = plt.subplots(figsize=(fig_w, fig_h))

    labels = [f"{t}s" for t in IDLE_TIMEOUTS]
    box_data = [[v / OCCUPANCY_SCALE for v in data[t]] for t in IDLE_TIMEOUTS]
    x = np.arange(1, len(IDLE_TIMEOUTS) + 1)

    ax_box.boxplot(
        box_data,
        positions=x,
        labels=labels,
        patch_artist=True,
        widths=0.5,
        showfliers=False,
        medianprops={"color": "#111111", "linewidth": 1.0},
        boxprops={"facecolor": OCCUPANCY_FILL, "edgecolor": OCCUPANCY_EDGE, "linewidth": 1.0},
        whiskerprops={"color": OCCUPANCY_EDGE, "linewidth": 1.0},
        capprops={"color": OCCUPANCY_EDGE, "linewidth": 1.0},
    )

    medians = {t: float(np.median(data[t])) for t in IDLE_TIMEOUTS}
    delays = [MEAN_DELAY_S[t] for t in IDLE_TIMEOUTS]
    delay_gap_pct = [gap_to_optimal_delay_pct(d) for d in delays]

    box_peak = max(v for series in box_data for v in series)
    gap_peak = max(delay_gap_pct) if delay_gap_pct else 0.0
    occ_ymax, gap_ymax = paired_axis_limits(box_peak, gap_peak)

    ax_box.set_xlabel("Idle Timeout $\\Delta$ (s)", fontsize=FONT_LABEL)
    style_occupancy_yaxis(ax_box, occ_ymax)
    ax_box.tick_params(axis="x", labelsize=FONT_TICK)
    ax_box.grid(True, axis="y", linestyle="--", alpha=0.35, linewidth=0.5)
    ax_box.set_axisbelow(True)

    ax_gap = ax_box.twinx()
    ax_gap.plot(
        x,
        delay_gap_pct,
        color=DELAY_COLOR,
        marker="o",
        markersize=5,
        markerfacecolor=DELAY_COLOR,
        markeredgecolor=DELAY_COLOR,
        linewidth=1.4,
        linestyle=":",
        zorder=3,
    )
    style_delay_gap_yaxis(ax_gap, gap_ymax)

    legend_handles = [
        Patch(
            facecolor=OCCUPANCY_FILL,
            edgecolor=OCCUPANCY_EDGE,
            linewidth=0.8,
            label="TCAM Occupancy",
        ),
        Line2D(
            [0],
            [0],
            color=DELAY_COLOR,
            marker="o",
            markersize=5,
            markerfacecolor=DELAY_COLOR,
            markeredgecolor=DELAY_COLOR,
            linewidth=1.4,
            linestyle=":",
            label="Delay Gap",
        ),
    ]
    ax_box.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        bbox_transform=ax_box.transAxes,
        ncol=2,
        fontsize=FONT_LEGEND,
        frameon=False,
        handlelength=1.4,
        columnspacing=1.0,
        borderpad=0.0,
        labelspacing=0.2,
    )
    fig.tight_layout()
    # Re-apply paired limits after layout so twin-axis ticks stay aligned (25 ↔ 125%, etc.).
    style_occupancy_yaxis(ax_box, occ_ymax)
    style_delay_gap_yaxis(ax_gap, gap_ymax)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    print(f"Wrote: {output_path}")
    print(f"Wrote: {output_path.with_suffix('.pdf')}")
    print("Median TCAM occupancy & delay gap:")
    for t in IDLE_TIMEOUTS:
        gap = gap_to_optimal_delay_pct(MEAN_DELAY_S[t])
        print(
            f"  Δ={t}s: median={medians[t]:.1f} flows "
            f"({medians[t] / OCCUPANCY_SCALE:.2f}×10²)  "
            f"E[D]={MEAN_DELAY_S[t]:.2f}s  gap={gap:.1f}%"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Box plot + delay gap for TCAM occupancy across idle timeouts."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data",
        help="Directory containing trace_1_sft_idle{N}s_int1s.csv files",
    )
    parser.add_argument("--stem", default="trace_1")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PNG path",
    )
    args = parser.parse_args()

    data = load_trace_data(args.raw_dir, args.stem)
    out = args.output or (
        args.raw_dir / f"{args.stem}_tcam_idle_timeout_comparison.png"
    )
    plot_comparison(data, out, trace_label=args.stem)


if __name__ == "__main__":
    main()
