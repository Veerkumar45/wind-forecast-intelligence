import json
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

ACTUALS_FILE = DATA_DIR / "wind_actuals_january_2026.json"
FORECASTS_FILE = DATA_DIR / "wind_forecasts_january_2026.json"

EXPECTED_START = "2026-01-01T00:00:00Z"
EXPECTED_END = "2026-02-01T00:00:00Z"


def load_json(path: Path) -> list[dict]:
    """Load JSON records and report clear input errors."""
    if not path.exists():
        raise ValueError(f"Required data file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            records = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read valid JSON from {path}: {error}") from error

    if not isinstance(records, list) or not records:
        raise ValueError(f"Expected a non-empty JSON list in {path.name}")

    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"Every record in {path.name} must be a JSON object")

    return records


def prepare_dataframe(
    records: list[dict],
    required_columns: set[str],
    timestamp_columns: list[str],
    numeric_columns: list[str],
    filename: str,
) -> pd.DataFrame:
    """Validate the required fields and convert timestamps/numeric columns."""
    df = pd.DataFrame(records)

    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{filename} is missing required columns: "
            f"{sorted(missing_columns)}"
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
    invalid_counts = df[checked_columns].isna().sum()
    invalid_counts = invalid_counts[invalid_counts > 0]

    if not invalid_counts.empty:
        details = ", ".join(
            f"{column}: {count}"
            for column, count in invalid_counts.items()
        )
        raise ValueError(
            f"{filename} contains missing or invalid required values: {details}"
        )

    for column in numeric_columns:
        if not df[column].map(lambda value: pd.notna(value) and abs(value) != float("inf")).all():
            raise ValueError(
                f"{filename} contains non-finite values in {column}"
            )

    return df


def validate_actuals() -> pd.DataFrame:
    """Validate half-hour actuals and aggregate them into hourly averages."""
    records = load_json(ACTUALS_FILE)

    df = prepare_dataframe(
        records=records,
        required_columns={"startTime", "fuelType", "generation"},
        timestamp_columns=["startTime"],
        numeric_columns=["generation"],
        filename=ACTUALS_FILE.name,
    )

    duplicate_count = int(df["startTime"].duplicated().sum())
    if duplicate_count:
        raise ValueError(
            f"{ACTUALS_FILE.name} contains {duplicate_count} duplicate "
            "delivery intervals"
        )

    expected = pd.date_range(
        start=EXPECTED_START,
        end=EXPECTED_END,
        freq="30min",
        inclusive="left",
    )

    actual_times = pd.DatetimeIndex(df["startTime"].unique())
    missing = expected.difference(actual_times)
    unexpected = actual_times.difference(expected)

    print("\n=== ACTUAL WIND GENERATION ===")
    print("Total records:", len(df))
    print("Fuel types:", df["fuelType"].unique())
    print("Missing values: 0")
    print("Duplicate delivery intervals:", duplicate_count)
    print("Expected half-hour intervals:", len(expected))
    print("Missing half-hour intervals:", len(missing))
    print("Unexpected half-hour intervals:", len(unexpected))

    if len(missing):
        print("First missing intervals:", list(missing[:10]))

    if len(unexpected):
        raise ValueError(
            f"{ACTUALS_FILE.name} contains timestamps outside January 2026"
        )

    if len(missing):
        raise ValueError(
            f"{ACTUALS_FILE.name} is missing {len(missing)} expected "
            "half-hour intervals"
        )

    hourly_actuals = (
        df.set_index("startTime")["generation"]
        .sort_index()
        .resample("1h")
        .mean()
        .rename("actual_generation")
        .reset_index()
    )

    missing_hourly = int(hourly_actuals["actual_generation"].isna().sum())
    print("Hourly actual records:", len(hourly_actuals))
    print("Missing hourly actual values:", missing_hourly)

    if missing_hourly:
        raise ValueError("Hourly actuals contain missing generation values")

    return hourly_actuals


def validate_forecasts() -> pd.DataFrame:
    """Validate forecast records and delivery/publication uniqueness."""
    records = load_json(FORECASTS_FILE)

    df = prepare_dataframe(
        records=records,
        required_columns={"startTime", "publishTime", "generation"},
        timestamp_columns=["startTime", "publishTime"],
        numeric_columns=["generation"],
        filename=FORECASTS_FILE.name,
    )

    duplicate_count = int(
        df.duplicated(subset=["startTime", "publishTime"]).sum()
    )

    print("\n=== WIND FORECASTS ===")
    print("Total records:", len(df))
    print("Missing values: 0")
    print("Unique delivery/publication pairs:",
          df[["startTime", "publishTime"]].drop_duplicates().shape[0])
    print("Duplicate delivery/publication pairs:", duplicate_count)
    print("Unique delivery hours:", df["startTime"].nunique())
    print("Unique publication times:", df["publishTime"].nunique())
    print("Earliest publication:", df["publishTime"].min())
    print("Latest publication:", df["publishTime"].max())
    print("Earliest delivery:", df["startTime"].min())
    print("Latest delivery:", df["startTime"].max())

    if duplicate_count:
        raise ValueError(
            f"{FORECASTS_FILE.name} contains {duplicate_count} duplicate "
            "delivery/publication pairs"
        )

    expected_hours = pd.date_range(
        start=EXPECTED_START,
        end=EXPECTED_END,
        freq="1h",
        inclusive="left",
    )

    delivery_hours = pd.DatetimeIndex(df["startTime"].unique())
    missing_hours = expected_hours.difference(delivery_hours)
    unexpected_hours = delivery_hours.difference(expected_hours)

    print("Expected delivery hours:", len(expected_hours))
    print("Missing forecast delivery hours:", len(missing_hours))
    print("Unexpected forecast delivery hours:", len(unexpected_hours))

    if len(missing_hours):
        print("First missing forecast hours:", list(missing_hours[:10]))
        raise ValueError(
            f"{FORECASTS_FILE.name} is missing {len(missing_hours)} "
            "delivery hours"
        )

    if len(unexpected_hours):
        raise ValueError(
            f"{FORECASTS_FILE.name} contains delivery hours outside January 2026"
        )

    return df


def main() -> int:
    """Run data-quality checks and return a process exit code."""
    try:
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

        print("\nDATA VALIDATION PASSED")
        return 0

    except (ValueError, OSError) as error:
        print(f"\nDATA VALIDATION FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())