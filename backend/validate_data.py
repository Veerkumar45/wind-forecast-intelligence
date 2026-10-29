from pathlib import Path

import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

ACTUALS_FILE = DATA_DIR / "wind_actuals_january_2026.json"
FORECASTS_FILE = DATA_DIR / "wind_forecasts_january_2026.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_actuals():
    records = load_json(ACTUALS_FILE)
    df = pd.DataFrame(records)

    df["startTime"] = pd.to_datetime(
        df["startTime"], utc=True
    )

    print("\n=== ACTUAL WIND GENERATION ===")
    print("Total records:", len(df))
    print("Fuel types:", df["fuelType"].unique())
    print("Missing values:")
    print(df[["startTime", "generation"]].isna().sum())

    print("Unique delivery intervals:", df["startTime"].nunique())
    print("Duplicate delivery intervals:", df["startTime"].duplicated().sum())

    expected = pd.date_range(
        start="2026-01-01T00:00:00Z",
        end="2026-02-01T00:00:00Z",
        freq="30min",
        inclusive="left",
    )

    actual_times = pd.DatetimeIndex(df["startTime"].unique())
    missing = expected.difference(actual_times)

    print("Expected half-hour intervals:", len(expected))
    print("Missing half-hour intervals:", len(missing))

    if len(missing):
        print("First missing intervals:", list(missing[:10]))

    # Convert half-hour actuals to hourly averages.
    hourly_actuals = (
        df.set_index("startTime")["generation"]
        .sort_index()
        .resample("1h")
        .mean()
        .rename("actual_generation")
        .reset_index()
    )

    print("Hourly actual records:", len(hourly_actuals))
    print(
        "Missing hourly actual values:",
        hourly_actuals["actual_generation"].isna().sum(),
    )

    return hourly_actuals


def validate_forecasts():
    records = load_json(FORECASTS_FILE)
    df = pd.DataFrame(records)

    df["startTime"] = pd.to_datetime(
        df["startTime"], utc=True
    )
    df["publishTime"] = pd.to_datetime(
        df["publishTime"], utc=True
    )

    print("\n=== WIND FORECASTS ===")
    print("Total records:", len(df))
    print("Missing values:")
    print(df[["startTime", "publishTime", "generation"]].isna().sum())

    print(
        "Unique delivery/publication pairs:",
        df[["startTime", "publishTime"]].drop_duplicates().shape[0],
    )

    print(
        "Duplicate delivery/publication pairs:",
        df.duplicated(subset=["startTime", "publishTime"]).sum(),
    )

    print("Unique delivery hours:", df["startTime"].nunique())
    print("Unique publication times:", df["publishTime"].nunique())

    print("Earliest publication:", df["publishTime"].min())
    print("Latest publication:", df["publishTime"].max())
    print("Earliest delivery:", df["startTime"].min())
    print("Latest delivery:", df["startTime"].max())

    return df


def main():
    hourly_actuals = validate_actuals()
    forecasts = validate_forecasts()

    actual_hours = set(hourly_actuals["startTime"])
    forecast_hours = set(forecasts["startTime"])

    print("\n=== DELIVERY COVERAGE ===")
    print("Actual delivery hours:", len(actual_hours))
    print("Forecast delivery hours:", len(forecast_hours))
    print(
        "Hours with both actuals and forecasts:",
        len(actual_hours & forecast_hours),
    )
    print(
        "Actual hours without any forecast:",
        len(actual_hours - forecast_hours),
    )


if __name__ == "__main__":
    main()