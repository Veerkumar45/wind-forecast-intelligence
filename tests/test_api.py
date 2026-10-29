import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make the backend directory importable when pytest runs from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Wind Forecast Intelligence API is running."
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert set(data["data_files"]) == {"day_ahead", "baseline", "daily"}
    assert all(isinstance(value, bool) for value in data["data_files"].values())


def test_summary_endpoint():
    response = client.get("/api/summary")

    assert response.status_code == 200

    data = response.json()
    assert data["period"] == "January 2026"
    assert data["forecast_type"] == "Day-ahead"
    assert data["hours_evaluated"] > 0

    for metric in ("mae", "rmse", "forecast_bias"):
        assert isinstance(data[metric], (int, float))

    assert data["mae"] >= 0
    assert data["rmse"] >= 0


def test_daily_accuracy_endpoint():
    response = client.get("/api/daily-accuracy")

    assert response.status_code == 200

    data = response.json()
    assert data["period"] == "January 2026"
    assert data["days_evaluated"] > 0
    assert len(data["results"]) == data["days_evaluated"]

    if data["results"]:
        assert {
            "delivery_date",
            "hours_evaluated",
            "MAE",
            "RMSE",
            "forecast_bias",
            "MAPE_percent",
        }.issubset(data["results"][0].keys())


def test_hourly_comparison_endpoint():
    response = client.get(
        "/api/hourly-comparison",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] == "2026-01-31"
    assert data["hours_returned"] == len(data["results"])

    if data["results"]:
        row = data["results"][0]
        assert {
            "timestamp",
            "actual_generation",
            "forecast_generation",
            "error",
            "absolute_error",
        }.issubset(row.keys())
        assert row["absolute_error"] >= 0


def test_hourly_comparison_rejects_invalid_date():
    response = client.get(
        "/api/hourly-comparison",
        params={"start_date": "invalid-date", "end_date": "2026-01-31"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Dates must use YYYY-MM-DD format."


def test_hourly_comparison_rejects_reversed_date_range():
    response = client.get(
        "/api/hourly-comparison",
        params={"start_date": "2026-01-20", "end_date": "2026-01-10"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "start_date must be earlier than or equal to end_date."
    )


def test_worst_days_endpoint():
    response = client.get("/api/worst-days", params={"limit": 5})

    assert response.status_code == 200

    data = response.json()
    assert len(data["results"]) <= 5

    if data["results"]:
        assert {"delivery_date", "MAE", "RMSE", "forecast_bias"}.issubset(
            data["results"][0].keys()
        )


@pytest.mark.parametrize("limit", [0, -1, 32, 100])
def test_worst_days_rejects_invalid_limit(limit):
    response = client.get("/api/worst-days", params={"limit": limit})

    assert response.status_code == 400
    assert response.json()["detail"] == "limit must be between 1 and 31."


def test_forecast_bias_endpoint():
    response = client.get("/api/forecast-bias")

    assert response.status_code == 200

    data = response.json()
    assert data["hours_evaluated"] > 0

    assert (
        data["overforecast_hours"]
        + data["underforecast_hours"]
        + data["exact_forecast_hours"]
        == data["hours_evaluated"]
    )

    assert isinstance(data["mean_forecast_bias"], (int, float))
    assert "Positive bias" in data["interpretation"]