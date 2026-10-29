import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PROJECT_ROOT / "backend" / "validate_data.py"

spec = importlib.util.spec_from_file_location(
    "wind_validator",
    VALIDATOR_PATH,
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def test_load_json_rejects_missing_file(tmp_path):
    missing_file = tmp_path / "missing.json"

    with pytest.raises(ValueError, match="Required data file not found"):
        validator.load_json(missing_file)


def test_prepare_dataframe_rejects_missing_columns():
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
        }
    ]

    with pytest.raises(ValueError, match="missing required columns"):
        validator.prepare_dataframe(
            records=records,
            required_columns={"startTime", "generation"},
            timestamp_columns=["startTime"],
            numeric_columns=["generation"],
            filename="sample.json",
        )


def test_prepare_dataframe_rejects_invalid_generation():
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "generation": "invalid",
        }
    ]

    with pytest.raises(ValueError, match="invalid required values"):
        validator.prepare_dataframe(
            records=records,
            required_columns={"startTime", "generation"},
            timestamp_columns=["startTime"],
            numeric_columns=["generation"],
            filename="sample.json",
        )


def test_actuals_reject_duplicate_intervals(monkeypatch):
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "fuelType": "WIND",
            "generation": 100,
        },
        {
            "startTime": "2026-01-01T00:00:00Z",
            "fuelType": "WIND",
            "generation": 110,
        },
    ]

    monkeypatch.setattr(validator, "load_json", lambda path: records)

    with pytest.raises(ValueError, match="duplicate delivery intervals"):
        validator.validate_actuals()


def test_actuals_reject_missing_half_hour_interval(monkeypatch):
    records = [
        {
            "startTime": "2026-01-01T00:00:00Z",
            "fuelType": "WIND",
            "generation": 100,
        }
    ]

    monkeypatch.setattr(validator, "load_json", lambda path: records)

    with pytest.raises(ValueError, match="missing 1487 expected"):
        validator.validate_actuals()


def test_forecasts_reject_duplicate_delivery_publication_pair(monkeypatch):
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

    monkeypatch.setattr(validator, "load_json", lambda path: records)

    with pytest.raises(ValueError, match="duplicate delivery/publication pairs"):
        validator.validate_forecasts()