"""Classify calibration input tables without performing calibration math.

This module answers only which known source schema a table follows and returns
its original values. Cumulative additions, concentrations, regression fits, and
correction factors belong in the processing layer where assumptions are explicit.
"""

from pathlib import Path

import pandas as pd

from .filename_metadata import parse_filename


# Historical tables sometimes include cumulative additions and sometimes only
# the individual additions. Both are valid inputs because cumulative volume can
# be derived later from the recorded additions.
SOLUTION_SCHEMAS = (
    {
        "Calibration_volume_ml",
        "Additions_of_secondary_ml",
        "Cumulative_secondary_solution_ml",
        "Conductivity",
    },
    {
        "Calibration_volume_ml",
        "additions_of_calibration_ml",
        "Conductivity",
    },
)

MASS_STOCK_SCHEMA = {
    "Calibration volume (ml)",
    "Calibration solution added (ml)",
    "Salt added (g)",
    "Concentration (g/mL)",
    "Conductivity",
}


def detect_calibration_type(columns):
    """Identify a supported calibration family from its required columns."""

    columns = set(columns)
    if any(required <= columns for required in SOLUTION_SCHEMAS):
        return "solution_injection"
    if MASS_STOCK_SCHEMA <= columns:
        return "mass_stock_titration"
    raise ValueError("Unsupported calibration table schema")


def read_calibration_table(path):
    """Read one recognized calibration CSV and attach schema provenance."""

    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Unsupported calibration table file type: {path.suffix.lower()}")

    df = pd.read_csv(path)
    calibration_type = detect_calibration_type(df.columns)

    metadata = {
        "source_file": str(path),
        "source_format": "csv",
        "source_type": "calibration",
        "instrument_family": "unknown",
        "filename_metadata": parse_filename(path),
        "embedded_metadata": {},
        "calibration_type": calibration_type,
    }
    return df, metadata
