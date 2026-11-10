"""Render the three discharge-summary figures from a published analysis bundle."""
from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BLUE = "#24547A"
ORANGE = "#A44B1A"
INK = "#222D35"


def _rows(bundle: Path, name: str) -> list[dict[str, str]]:
    with (bundle / "tables" / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _label(row: dict[str, str]) -> str:
    day = date.fromisoformat(row["field_date"])
    flag = "*" if row["source_background_discrepancy"].lower() == "true" else ""
    return f"{day:%b} {day.day}  {row['trial_id'].split('-')[-1]}{flag}"


def _base(title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(7, 5.7), dpi=180)
    fig.subplots_adjust(left=.21, right=.96, top=.75, bottom=.29)
    fig.text(.05, .96, title, fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(.05, .88, subtitle, fontsize=11, color=INK, va="top")
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#DDE3E6", linewidth=.7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, labelsize=11, colors=INK, pad=6)
    return fig, ax


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, facecolor="white", metadata={"Software": "matplotlib"})
    plt.close(fig)


def render_summary(bundle: Path, figure_dir: Path) -> None:
    """Write the mass, window review and calibration reuse summary PNGs."""
    bundle, figure_dir = Path(bundle), Path(figure_dir)
    primary = _rows(bundle, "discharge_primary.csv")
    if not primary or any(row["conductivity_basis"] != "specific" for row in primary):
        raise ValueError("These reviewed figures require specific-conductivity primary estimates")
    y = np.arange(len(primary))
    labels = [_label(r) for r in primary]
    flagged = [label.rstrip('*') for label in labels if label.endswith('*')]
    flag_note = f"* {', '.join(flagged)}: background discrepancy.\n" if flagged else ""
    dates = [date.fromisoformat(r["field_date"]) for r in primary]
    period = dates[0].strftime("%B %Y") if len({(d.year, d.month) for d in dates}) == 1 else f"{min(dates):%Y-%m-%d} to {max(dates):%Y-%m-%d}"
    sites = ", ".join(sorted({r["site_alias"] for r in primary})).replace("NISQ", "Nisqually River")

    specific = [float(r["q_primary_m3_s"]) for r in primary]
    actual = [(i, float(r["q_actual_comparison_m3_s"])) for i, r in enumerate(primary) if r["q_actual_comparison_m3_s"].strip()]
    title = "Actual conductivity gives higher Q" if actual and all(v > specific[i] for i, v in actual) else "Proposed Q by conductivity channel"
    fig, ax = _base(title, f"{len(primary)} releases • {sites} • {period}")
    ax.scatter(specific, y - .10, s=55, color=BLUE, label="Specific conductivity (primary)", zorder=3)
    if actual:
        ax.scatter([v for _, v in actual], [i + .10 for i, _ in actual], s=58, color=ORANGE, marker="s",
                   label="Actual conductivity (comparison)", zorder=3)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(left=min(0, min(specific + [v for _, v in actual])), right=max(specific + [v for _, v in actual]) * 1.15)
    ax.set_xlabel("Discharge Q (m³/s)", fontsize=11)
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="lower left", bbox_to_anchor=(.045, .76),
               frameon=False, fontsize=11, ncols=2)
    fig.text(.05, .19, flag_note + "Proposed; mixing, recovery and total uncertainty unresolved.\nSee the separate window and background sensitivity figure.", fontsize=11, color=INK, va="top")
    fig.text(.05, .025, "Source: Discharge analysis, primary estimates", fontsize=11, color=INK)
    _save(fig, figure_dir / "mass/discharge_comparison.png")

    fig, ax = _base("Window and background choices shift Q", f"Numerical review • specific conductivity • {period}")
    low = [100 * float(r["local_sensitivity_min_relative"]) for r in primary]
    high = [100 * float(r["local_sensitivity_max_relative"]) for r in primary]
    ax.axvline(0, color="#7B898F", linewidth=1)
    ax.hlines(y, low, high, color=BLUE, linewidth=5)
    ax.scatter(low, y, color=BLUE, s=28, zorder=3)
    ax.scatter(high, y, color=BLUE, s=28, zorder=3)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    bound = max(abs(v) for v in low + high) * 1.2 or 1
    ax.set_xlim(-bound, bound)
    ax.set_xlabel("Change from proposed Q (%)", fontsize=11)
    fig.text(.05, .19, flag_note + "Scenario sensitivity, not confidence intervals\nor total Q uncertainty.", fontsize=11, color=INK, va="top")
    fig.text(.05, .025, "Source: Discharge analysis, numerical window review", fontsize=11, color=INK)
    _save(fig, figure_dir / "review/window_background_sensitivity.png")

    reuse = {r["conductivity_basis"]: r for r in _rows(bundle, "coefficient_reuse.csv")}
    spec, act = reuse["specific"], reuse["actual"]
    title = "Specific reuse fails the Q criterion" if spec["outcome"] == "fail" else "Calibration reuse and the Q criterion"
    subtitle = f"{spec['session_count']} sessions • {spec['day_count']} days • sensor {spec['sensor_serial']}"
    fig, ax = _base(title, subtitle)
    all_values = []
    for i, basis in enumerate(("specific", "actual")):
        effects = json.loads(reuse[basis]["lodo_effects"])
        vals = [100 * float(e["q_relative_effect"]) for e in effects]
        all_values.extend(vals)
        ax.scatter(vals, i + np.linspace(-.13, .13, len(vals)), s=54, color=BLUE if basis == "specific" else ORANGE,
                   marker="o" if basis == "specific" else "s", zorder=3)
    tolerance = 100 * float(spec["tolerance_q"])
    ax.axvline(-tolerance, color="#717C82", linestyle="--", linewidth=1)
    ax.axvline(tolerance, color="#717C82", linestyle="--", linewidth=1)
    ax.set_yticks([0, 1], ["Specific", "Actual"])
    ax.set_ylim(1.6, -.6)
    bound = max([tolerance] + [abs(v) for v in all_values]) * 1.2 or 1
    ax.set_xlim(-bound, bound)
    ax.set_xlabel("Estimated Q change using shared K (%)", fontsize=11)
    outcome = "Actual reuse inconclusive: temperature model unavailable." if act["outcome"] == "insufficient_evidence" else f"Actual reuse outcome: {act['outcome'].replace('_', ' ')}."
    fig.text(.05, .19, f"Leave-one-day-out effects; dashed lines: ±{tolerance:g}% Q.\n{outcome}", fontsize=11, color=INK, va="top")
    fig.text(.05, .025, "Source: Discharge analysis, calibration reuse test", fontsize=11, color=INK)
    _save(fig, figure_dir / "reuse/calibration_consistency.png")
