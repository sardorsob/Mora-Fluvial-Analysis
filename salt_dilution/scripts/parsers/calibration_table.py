"""Read calibration CSVs and identify their table format.

The columns tell us whether a table uses the solution-injection or mass/stock
format. Calculating cumulative additions, concentrations and fitted correction
factors is a separate step in scripts/processing/.
"""

from pathlib import Path

import pandas as pd

from .filename_metadata import parse_filename


# Some field tables record a running total; others record each addition only.
# Accept either layout and leave cumulative-volume calculations to processing.
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
    """Match the column names to a known calibration format, or raise an error."""

    columns = set(columns)
    if any(required <= columns for required in SOLUTION_SCHEMAS):
        return "solution_injection"
    if MASS_STOCK_SCHEMA <= columns:
        return "mass_stock_titration"
    raise ValueError("Unsupported calibration table schema")


def read_calibration_table(path):
    """Return the calibration table with its source details and format name."""

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
