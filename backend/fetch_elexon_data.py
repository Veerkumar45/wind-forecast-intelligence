
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()


def fetch_dataset(dataset_name, start, end):
    """Fetch a dataset in one-day publication-time windows."""
    records = {}
    window_start = start

    while window_start < end:
        window_end = min(
            window_start + timedelta(days=1),
            end,
        )

        params = {
            "publishDateTimeFrom": window_start.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "publishDateTimeTo": window_end.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

        if dataset_name == "FUELHH":
            params["fuelType"] = "WIND"

        print(
            f"{dataset_name}: "
            f"{params['publishDateTimeFrom']} "
            f"to {params['publishDateTimeTo']}"
        )

        response = SESSION.get(
            f"{BASE_URL}/{dataset_name}/stream",
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        batch = response.json()

        if not isinstance(batch, list):
            raise ValueError(
                f"Unexpected response format for {dataset_name}"
            )

        print(f"  Received {len(batch)} records")

        for record in batch:
            # Preserve records from different forecast publications.
            key = json.dumps(record, sort_keys=True)
            records[key] = record

        window_start = window_end
        time.sleep(0.2)

    return list(records.values())


def filter_delivery_month(records):
    """Keep delivery intervals occurring in January 2026."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, tzinfo=timezone.utc)

    filtered = []

    for record in records:
        delivery_time = datetime.fromisoformat(
            record["startTime"].replace("Z", "+00:00")
        )

        if start <= delivery_time < end:
            filtered.append(record)

    return filtered


def save_json(filename, records):
    path = OUTPUT_DIR / filename
    path.write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(records)} records to {path.resolve()}")


def main():
    # Actuals can be published through February 1 for January delivery.
    actual_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    actual_end = datetime(2026, 2, 1, tzinfo=timezone.utc)

    # Fetch earlier forecast publications to capture forecasts
    # for delivery intervals at the beginning of January.
    forecast_start = datetime(2025, 12, 29, tzinfo=timezone.utc)
    forecast_end = datetime(2026, 2, 1, tzinfo=timezone.utc)

    print("\nFetching actual wind generation...")
    actual_records = fetch_dataset(
        "FUELHH",
        actual_start,
        actual_end,
    )
    actual_records = filter_delivery_month(actual_records)
    save_json("wind_actuals_january_2026.json", actual_records)

    print("\nFetching wind forecasts...")
    forecast_records = fetch_dataset(
        "WINDFOR",
        forecast_start,
        forecast_end,
    )
    forecast_records = filter_delivery_month(forecast_records)
    save_json("wind_forecasts_january_2026.json", forecast_records)

    print("\nDownload summary")
    print("Actual wind records:", len(actual_records))
    print("Forecast records:", len(forecast_records))


if __name__ == "__main__":
    main()