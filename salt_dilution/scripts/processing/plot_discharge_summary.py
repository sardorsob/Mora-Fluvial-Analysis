"""Render release and calibration figures from the saved analysis tables."""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date
import json
import math
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np

BLUE = "#24547A"
ORANGE = "#A44B1A"
INK = "#222D35"
GRAY = "#596971"
SITE_NAMES = {"NISQ": "Nisqually River", "PAR": "Paradise"}
METHOD_NAMES = {"mass_slug": "Mass slug", "solution_slug": "Solution slug"}
CHANNEL_STYLE = {"specific": (BLUE, "o"), "actual": (ORANGE, "s")}
CONDITIONAL_SUPPORT = {"conditional_calibration_variant", "conditional_reported_volume"}


def _rows(bundle: Path, name: str, *, optional=False) -> list[dict[str, str]]:
    path = bundle / "tables" / name
    if optional and not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _number(value):
    if value in (None, ""):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Nonfinite value in discharge chart data: {value}")
    return result


def _unique_releases(rows):
    if len({r["trial_id"] for r in rows}) != len(rows):
        raise ValueError("Discharge chart data contain a duplicate release")


def _channel_points(primary):
    _unique_releases(primary)
    points = []
    for i, row in enumerate(primary):
        value = _number(row["q_primary_m3_s"])
        channel = row["conductivity_basis"]
        if value is None or value <= 0 or channel not in CHANNEL_STYLE:
            raise ValueError(f"Invalid primary discharge for {row['trial_id']}")
        points.append((i, channel, value))
        actual = _number(row.get("q_actual_comparison_m3_s"))
        if channel == "specific" and actual is not None:
            if actual <= 0:
                raise ValueError(f"Invalid comparison discharge for {row['trial_id']}")
            points.append((i, "actual", actual))
    return points


def _recovery_counts(rows):
    _unique_releases(rows)
    groups = defaultdict(lambda: [0, 0, 0, 0])
    for row in rows:
        counts = groups[row["field_date"], row["site_alias"]]
        value = _number(row["q_primary_m3_s"])
        if value is not None:
            if value <= 0 or row["case_disposition"] == "excluded_practice":
                raise ValueError(f"Invalid plotted release discharge: {row['trial_id']}")
            counts[int(row.get("estimate_support") in CONDITIONAL_SUPPORT)] += 1
        elif row["case_disposition"] == "excluded_practice":
            counts[3] += 1
        else:
            counts[2] += 1
    return {key: tuple(value) for key, value in groups.items()}


def _label(row, *, site=False, method=False):
    day = date.fromisoformat(row["field_date"])
    flag = "*" if row.get("source_background_discrepancy", "").lower() == "true" else ""
    label = f"{day:%d %b %Y} · {row['trial_id'].rsplit('-', 1)[-1]}{flag}"
    if site:
        label = f"{row['site_alias']} · " + label
    if method:
        label += f"\n{METHOD_NAMES.get(row.get('discharge_method') or 'mass_slug', '')}"
    return label


def _period(rows):
    dates = sorted({date.fromisoformat(r["field_date"]) for r in rows})
    if len(dates) == 1:
        return dates[0].strftime("%d %B %Y")
    if len({(day.year, day.month) for day in dates}) == 1:
        return f"{dates[0].day}–{dates[-1].day} {dates[0]:%B %Y}"
    return f"{dates[0]:%d %b %Y} – {dates[-1]:%d %b %Y}"


def _base(title, subtitle, *, row_count=0, left=.26, extra_line=False, width=7.8, panels=None):
    height = max(5.15, 2.8 + row_count * (.44 if extra_line else .31))
    if panels:
        height += 1.5*(len(panels)-1)
    fig, axes = plt.subplots(len(panels) if panels else 1, 1, squeeze=False,
                             height_ratios=panels, figsize=(width, height), dpi=180)
    fig.subplots_adjust(left=left, right=.96, top=1-(1.40 if panels else 1.19)/height,
                        bottom=1.46/height, hspace=.68)
    fig.text(.05, 1-.23/height, title, fontsize=16, fontweight="bold", color=INK, va="top")
    fig.text(.05, 1-.56/height, subtitle, fontsize=12, color=INK, va="top")
    for ax in axes[:, 0]:
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#DDE3E6", linewidth=.7)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0, labelsize=12, colors=INK, pad=6)
    return fig, axes[:, 0] if panels else axes[0, 0]


def _footer(fig, note, source):
    height = fig.get_figheight()
    wrapped = "\n".join(textwrap.fill(line, 76) for line in note.splitlines())
    extra = .19*max(0, len(wrapped.splitlines())-3)
    if extra:
        fig.subplots_adjust(bottom=(1.46+extra)/height)
    fig.text(.05, (.91+extra)/height, wrapped, fontsize=12, color=INK, va="top")
    fig.text(.05, .13/height, source, fontsize=12, color=INK, va="bottom")


def _legend(fig, ax, *, handles=None):
    handles = ax.get_legend_handles_labels()[0] if handles is None else handles
    if handles:
        fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.041, 1-1.14/fig.get_figheight()),
                   frameon=False, fontsize=12, ncols=len(handles))


def _save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, facecolor="white", metadata={"Software": "matplotlib"})
    plt.close(fig)


def _comparison_panel(ax, rows, *, mixed_methods):
    points = _channel_points(rows)
    labels = [_label(row, method=mixed_methods) for row in rows]
    for channel, (color, marker) in CHANNEL_STYLE.items():
        paired = {i for i, other, _ in points if other != channel}
        for hollow in (False, True):
            channel_points = [(i, value) for i, basis, value in points if basis == channel
                              and (rows[i].get("estimate_support") in CONDITIONAL_SUPPORT) == hollow]
            if channel_points:
                ax.scatter([value for _, value in channel_points],
                           [i + ((.13 if channel == "actual" else -.13) if i in paired else 0) for i, _ in channel_points],
                           s=50, facecolors="none" if hollow else color, edgecolors=color, linewidth=1.5,
                           marker=marker, zorder=3)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(len(labels)-.46, -.54)
    ax.set_xlim(0, max(value for _, _, value in points)*1.14)
    ax.set_xlabel("Discharge Q (m³/s)", fontsize=12)
    return {channel for _, channel, _ in points}


def _comparison(primary):
    _unique_releases(primary)
    by_site = defaultdict(list)
    for row in primary:
        by_site[row["site_alias"]].append(row)
    sites = sorted(by_site)
    methods = {r.get("discharge_method") or "mass_slug" for r in primary}
    supports = {r.get("estimate_support") for r in primary}
    conditional = bool(supports & CONDITIONAL_SUPPORT)
    multi_site = len(sites) > 1
    context = "Separate scales by site" if multi_site else SITE_NAMES.get(sites[0], sites[0])
    if len(methods) == 1:
        method_label = METHOD_NAMES.get(next(iter(methods)), "")
        context += f" · {method_label.lower()}" if method_label else ""
    subtitle = f"{len(primary)} releases · {context} · {_period(primary)}"
    title = "Proposed and conditional discharge" if conditional else "Proposed discharge by release"
    panels = [max(2, len(by_site[site])) for site in sites] if multi_site else None
    fig, axes = _base(title, subtitle, row_count=len(primary), extra_line=len(methods)>1, panels=panels)
    displayed = set()
    for site, ax in zip(sites, axes if multi_site else [axes]):
        rows = by_site[site]
        displayed.update(_comparison_panel(ax, rows, mixed_methods=len(methods)>1))
        if multi_site:
            only_conditional = all(r.get("estimate_support") in CONDITIONAL_SUPPORT for r in rows)
            only_proposed = all(r.get("estimate_support") not in CONDITIONAL_SUPPORT for r in rows)
            status = " · Conditional" if only_conditional else " · Proposed" if only_proposed else ""
            ax.set_title(SITE_NAMES.get(site, site)+status, loc="left", fontsize=13, fontweight="bold", color=INK)
    _legend(fig, fig.axes[0], handles=[Line2D([], [], color=color, marker=marker, linestyle="none",
                                             label=f"{channel.title()} conductivity")
                                       for channel, (color, marker) in CHANNEL_STYLE.items() if channel in displayed])
    flagged = any(r.get("source_background_discrepancy", "").lower() == "true" for r in primary)
    note = "Mixing, recovery and total uncertainty remain unquantified."
    if "conditional_calibration_variant" in supports:
        note += "\nOpen worksheet estimates assume alternate calibration and nominal salt delivery."
    if "conditional_reported_volume" in supports:
        note += "\nOpen solution estimates assume the reported volume was delivered."
    if flagged:
        note += "\n* Background discrepancy in the field note."
    _footer(fig, note, "Source · Mount Rainier Fluvial Analysis, primary discharge estimates")
    return fig


def _sensitivity(primary):
    rows = [(row, _number(row.get("local_sensitivity_min_relative")), _number(row.get("local_sensitivity_max_relative")))
            for row in primary]
    rows = [(row, lo*100, hi*100) for row, lo, hi in rows if lo is not None and hi is not None]
    if not rows:
        return None
    data = [row for row, _, _ in rows]
    y = np.arange(len(rows))
    low = [lo for _, lo, _ in rows]
    high = [hi for _, _, hi in rows]
    multiple_sites = len({r["site_alias"] for r in data}) > 1
    fig, ax = _base("Window and background sensitivity", f"{len(rows)} releases · Primary conductivity channel · {_period(data)}",
                    row_count=len(rows), left=.35 if multiple_sites else .29)
    ax.axvline(0, color="#717C82", linewidth=1)
    ax.hlines(y, low, high, color=BLUE, linewidth=4)
    ax.scatter(low, y, color=BLUE, s=28, zorder=3)
    ax.scatter(high, y, color=BLUE, s=28, zorder=3)
    ax.set_yticks(y, [_label(r, site=multiple_sites).rstrip("*") for r in data])
    ax.set_ylim(len(rows)-.46, -.54)
    bound = max(abs(v) for v in low + high)*1.2 or 1
    ax.set_xlim(-bound, bound)
    ax.set_xlabel("Change from the saved Q estimate (%)", fontsize=12)
    _footer(fig, "Ranges show only the tested window and background choices.",
            "Source · Mount Rainier Fluvial Analysis, numerical window review")
    return fig


def _reuse(rows):
    if not rows:
        return None
    fig, ax = _base("Discharge sensitivity to calibration reuse", "Leave-one-day-out checks by sensor and conductivity channel",
                    row_count=len(rows), left=.33, extra_line=True)
    bounds = []
    labels = []
    for i, row in enumerate(rows):
        color, marker = CHANNEL_STYLE[row["conductivity_basis"]]
        values = [100*float(e["q_relative_effect"]) for e in json.loads(row["lodo_effects"] or "[]")]
        tolerance = 100*float(row["tolerance_q"])
        if values:
            ax.scatter(values, i+np.linspace(-.14, .14, len(values)), s=50, color=color, marker=marker, zorder=3)
        else:
            ax.text(0, i, "No usable checks", color=GRAY, fontsize=12, ha="center", va="center")
        ax.vlines([-tolerance, tolerance], i-.33, i+.33, color="#717C82", linestyle="--", linewidth=1)
        bounds += [tolerance, *[abs(v) for v in values]]
        outcome = {"pass": "Passed", "fail": "Failed", "insufficient_evidence": "Inconclusive"}.get(
            row["outcome"], row["outcome"].replace("_", " ").capitalize())
        channel = row["conductivity_basis"].title()
        day_unit = 'day' if int(row['day_count']) == 1 else 'days'
        labels.append(f"{channel} · {row['sensor_serial']}\n{outcome} · {row['day_count']} {day_unit}")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(len(labels)-.47, -.53)
    bound = max(bounds)*1.2 or 1
    ax.set_xlim(-bound, bound)
    ax.set_xlabel("Estimated Q change using shared K (%)", fontsize=12)
    _footer(fig, "Dashed markers show the Q tolerance for each calibration group.",
            "Source · Mount Rainier Fluvial Analysis, calibration reuse test")
    return fig


def _recovery(rows, scenarios=()):
    counts = _recovery_counts(rows)
    keys = sorted(counts)
    totals = np.array([counts[key] for key in keys])
    fig, ax = _base(f"Selected discharge for {totals[:, :2].sum()} of {len(rows)} releases",
                    "Release counts by field date and site", row_count=len(keys), left=.27)
    y = np.arange(len(keys))
    left = np.zeros(len(keys), dtype=int)
    styles = (("Proposed Q", BLUE, BLUE, ""), ("Conditional Q", "white", BLUE, "..."),
              ("No selected Q", "#C6CFD4", "#C6CFD4", ""), ("Practice", "white", GRAY, "///"))
    for amounts, (label, color, edge, hatch) in zip(totals.T, styles):
        visible = amounts > 0
        if visible.any():
            ax.barh(y[visible], amounts[visible], left=left[visible], color=color, edgecolor=edge,
                    hatch=hatch, label=label, height=.64)
        left += amounts
    ax.set_yticks(y, [f"{date.fromisoformat(day):%d %b %Y} · {site}" for day, site in keys])
    ax.set_ylim(len(keys)-.45, -.55)
    ax.set_xlim(0, max(left)+.4)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Recorded releases", fontsize=12)
    _legend(fig, ax)
    note = 'Each release is counted once.'
    if scenarios:
        count = len({r['trial_id'] for r in scenarios})
        note += f"\n{count} additional release{'s have' if count != 1 else ' has'} capture-assumed scenarios shown separately."
    _footer(fig, note,
            "Source · Mount Rainier Fluvial Analysis, discharge by release")
    return fig


def _calibration_reference(rows):
    fits = [(r, _number(r["k"]), _number(r["nacl_reference_k"])) for r in rows
            if r["conductivity_basis"] == "specific" and r["calibration_basis"] == "mass_concentration"]
    fits = [(r, k, ref) for r, k, ref in fits if k is not None and k > 0 and ref is not None and ref > 0]
    if not fits:
        return None
    dates = [date.fromisoformat(r["field_date"]) for r, _, _ in fits]
    sites = sorted({r.get("site_alias") or r["calibration_id"].split("-", 1)[0] for r, _, _ in fits})
    preparation_count = len({r["calibration_id"] for r, _, _ in fits})
    fig, ax = _base("Specific-conductivity calibration and dilute NaCl",
                    f"{preparation_count} preparations · Mass-concentration slopes · {_period([r for r, _, _ in fits])}", left=.16)
    for index, site in enumerate(sites):
        indices = [i for i, (r, _, _) in enumerate(fits)
                   if (r.get("site_alias") or r["calibration_id"].split("-", 1)[0]) == site]
        color, marker = (BLUE, "o") if index == 0 else (ORANGE, "s")
        slopes = [fits[i][1] for i in indices]
        days = [dates[i] for i in indices]
        ax.scatter(days, slopes, color=color, marker=marker, s=34, alpha=.9, zorder=3,
                   label=SITE_NAMES.get(site, site))
        errors = [(dates[i], fits[i][1], _number(fits[i][0].get("k_se"))) for i in indices]
        for day, value, error in errors:
            if error is not None:
                ax.errorbar(day, value, yerr=error, fmt="none", ecolor=color, linewidth=1, capsize=2)
    references = {round(ref, 12) for _, _, ref in fits}
    if len(references) != 1:
        raise ValueError("Specific mass-calibration reference varies across rows")
    ax.axhline(next(iter(references)), color=GRAY, linestyle="--", linewidth=1.1, label="Ideal dilute NaCl at 25 °C")
    locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y" if (max(dates)-min(dates)).days > 120 else "%d %b"))
    ax.set_xlabel("Field date", fontsize=12)
    ax.set_ylabel("K (mg/L per µS/cm)", fontsize=12)
    ax.grid(False, axis="x")
    ax.grid(True, axis="y", color="#DDE3E6", linewidth=.7)
    _legend(fig, ax)
    _footer(fig, "Whiskers show one fit standard error.\nThe NaCl line assumes ideal dilution at 25 °C.",
            "Source · Mount Rainier Fluvial Analysis, calibration diagnostics")
    return fig


def _conditional_capture(rows):
    if not rows:
        return None
    fig, ax = _base("Conditional discharge if the captured pulse is complete",
                    "Observed pulse intervals · Capture assumption unresolved", row_count=len(rows), left=.31)
    values = [_number(r["q_m3_s"]) for r in rows]
    if any(value is None or value <= 0 for value in values):
        raise ValueError("Invalid conditional capture discharge")
    for i, row in enumerate(rows):
        color, marker = CHANNEL_STYLE[row["conductivity_basis"]]
        ax.scatter(values[i], i, marker=marker, s=65, facecolors="none", edgecolors=color, linewidth=1.5)
    labels = [f"{_label(row, site=True)}\n{row['conductivity_basis'].title()} conductivity"
              for row in (dict(r, site_alias=r.get("site_alias") or r["trial_id"].split("-", 1)[0]) for r in rows)]
    ax.set_yticks(range(len(rows)), labels)
    ax.set_ylim(len(rows)-.44, -.56)
    ax.set_xlim(0, max(values)*1.15)
    ax.set_xlabel("Conditional discharge Q (m³/s)", fontsize=12)
    _footer(fig, "These scenarios are separate from the proposed release estimates.",
            "Source · Mount Rainier Fluvial Analysis, conditional discharge scenarios")
    return fig


def render_summary(bundle: Path, figure_dir: Path) -> set[Path]:
    """Write figures supported by the saved rows and return their relative paths."""
    bundle, figure_dir = Path(bundle), Path(figure_dir)
    primary = sorted(_rows(bundle, "discharge_primary.csv"), key=lambda r: (r["field_date"], r["trial_id"]))
    releases = _rows(bundle, "discharge_by_release.csv")
    scenarios = _rows(bundle, "conditional_discharge.csv", optional=True)
    figures = {
        "mass/discharge_comparison.png": _comparison(primary) if primary else None,
        "review/window_background_sensitivity.png": _sensitivity(primary),
        "reuse/calibration_consistency.png": _reuse(_rows(bundle, "coefficient_reuse.csv")),
        "review/recovery_by_date.png": _recovery(releases, scenarios) if releases else None,
        "review/calibration_reference.png": _calibration_reference(_rows(bundle, "calibration_quality.csv", optional=True)),
        "review/conditional_discharge.png": _conditional_capture(scenarios),
    }
    rendered = set()
    for name, figure in figures.items():
        if figure is not None:
            path = Path(name)
            _save(figure, figure_dir / path)
            rendered.add(path)
    return rendered
