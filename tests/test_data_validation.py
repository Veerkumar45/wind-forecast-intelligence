import json

import pandas as pd
import pytest

from pathlib import Path


def load_json(path):
    """Load JSON records from a file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_records(records, required_columns, timestamp_columns, numeric_columns):
    """Validate required columns, timestamps, and numeric values."""
    df = pd.DataFrame(records)

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    for column in timestamp_columns:
        df[column] = pd.to_datetime(
            df[column],
            utc=True,
            errors="coerce",
        )

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    checked_columns = timestamp_columns + numeric_columns

    if df[checked_columns].isna().any().any():
        raise ValueError(
            "Invalid or missing timestamp/numeric values detected."
        )

    return df


def test_load_json_rejects_missing_file(tmp_path):
    missing_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_json(missing_file)


def test_validate_records_rejects_missing_columns():
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
        }
    ]

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_records(
            records=records,
            required_columns=["startTime", "generation"],
            timestamp_columns=["startTime"],
            numeric_columns=["generation"],
        )


def test_validate_records_rejects_invalid_timestamp():
    records = [
        {
            "startTime": "not-a-timestamp",
            "generation": 100,
        }
    ]

    with pytest.raises(ValueError, match="Invalid or missing"):
        validate_records(
            records=records,
            required_columns=["startTime", "generation"],
            timestamp_columns=["startTime"],
            numeric_columns=["generation"],
        )


@pytest.mark.parametrize("generation", [None, "invalid"])
def test_validate_records_rejects_invalid_generation(generation):
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "generation": generation,
        }
    ]

    with pytest.raises(ValueError, match="Invalid or missing"):
        validate_records(
            records=records,
            required_columns=["startTime", "generation"],
            timestamp_columns=["startTime"],
            numeric_columns=["generation"],
        )


def test_forecast_delivery_publication_pairs_are_unique():
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T12:00:00Z",
            "generation": 100,
        },
        {
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2025-12-31T12:00:00Z",
            "generation": 110,
        },
    ]

    df = pd.DataFrame(records)

    duplicate_count = df.duplicated(
        subset=["startTime", "publishTime"]
    ).sum()

    assert duplicate_count == 1