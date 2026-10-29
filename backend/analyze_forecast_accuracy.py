
import json
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DATA_DIR = Path("data")

ACTUALS_FILE = DATA_DIR / "wind_actuals_january_2026.json"
FORECASTS_FILE = DATA_DIR / "wind_forecasts_january_2026.json"

# Working assumption for the assessment:
# Select forecasts available by noon UTC on the
# calendar day before the delivery date.
DECISION_CUTOFF_HOUR_UTC = 12


# --------------------------------------------------
# Load data
# --------------------------------------------------

def load_json(path):
    """Load records from a JSON file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_actuals():
    """Aggregate half-hourly actual generation into hourly values."""
    actuals = pd.DataFrame(load_json(ACTUALS_FILE))

    actuals["startTime"] = pd.to_datetime(
        actuals["startTime"],
        utc=True,
    )

    actuals["generation"] = pd.to_numeric(
        actuals["generation"],
        errors="coerce",
    )

    hourly_actuals = (
        actuals
        .set_index("startTime")["generation"]
        .sort_index()
        .resample("1h")
        .mean()
        .rename("actual_generation")
        .reset_index()
    )

    return hourly_actuals


def load_forecasts():
    """Load forecasts with their publication timestamps."""
    forecasts = pd.DataFrame(load_json(FORECASTS_FILE))

    forecasts["startTime"] = pd.to_datetime(
        forecasts["startTime"],
        utc=True,
    )

    forecasts["publishTime"] = pd.to_datetime(
        forecasts["publishTime"],
        utc=True,
    )

    forecasts["generation"] = pd.to_numeric(
        forecasts["generation"],
        errors="coerce",
    )

    return forecasts.rename(
        columns={"generation": "forecast_generation"}
    )


# --------------------------------------------------
# Inspect forecast publication schedule
# --------------------------------------------------

def inspect_publication_schedule(forecasts):
    """Display the timing and size of forecast publications."""
    print("\n" + "=" * 55)
    print("FORECAST PUBLICATION SCHEDULE")
    print("=" * 55)

    publication_times = (
        forecasts["publishTime"]
        .drop_duplicates()
        .sort_values()
    )

    print("Number of publication times:", len(publication_times))

    print("\nFirst 15 publication times:")
    print(publication_times.head(15).to_string(index=False))

    print("\nLast 15 publication times:")
    print(publication_times.tail(15).to_string(index=False))

    records_per_publication = forecasts.groupby("publishTime").size()

    print("\nForecast records per publication:")
    print(records_per_publication.describe().round(2).to_string())

    intervals = publication_times.diff().dropna()

    print("\nMost common intervals between publications:")

    if intervals.empty:
        print("Not enough publication times.")
    else:
        print(intervals.value_counts().head(10).to_string())


# --------------------------------------------------
# Calculate forecast metrics
# --------------------------------------------------

def calculate_metrics(comparison):
    """Calculate standard forecast accuracy metrics."""
    if comparison.empty:
        return {
            "records_evaluated": 0,
            "MAE": None,
            "RMSE": None,
            "Forecast_Bias": None,
            "MAPE_percent": None,
        }

    actual = comparison["actual_generation"]
    forecast = comparison["forecast_generation"]

    errors = forecast - actual
    absolute_errors = errors.abs()

    nonzero_actuals = actual != 0

    if nonzero_actuals.any():
        mape = (
            absolute_errors[nonzero_actuals]
            / actual[nonzero_actuals].abs()
        ).mean() * 100
    else:
        mape = np.nan

    return {
        "records_evaluated": len(comparison),
        "MAE": round(float(absolute_errors.mean()), 3),
        "RMSE": round(float(np.sqrt((errors ** 2).mean())), 3),
        "Forecast_Bias": round(float(errors.mean()), 3),
        "MAPE_percent": (
            round(float(mape), 2)
            if pd.notna(mape)
            else None
        ),
    }


def print_metrics(title, comparison):
    """Print accuracy metrics and coverage information."""
    print("\n" + "=" * 55)
    print(title)
    print("=" * 55)

    metrics = calculate_metrics(comparison)

    for name, value in metrics.items():
        print(f"{name}: {value}")

    return metrics


# --------------------------------------------------
# Baseline evaluation
# --------------------------------------------------

def evaluate_baseline(actuals, forecasts):
    """
    Select the latest forecast published no later than
    the start of its delivery hour.

    This is a technical baseline, not the day-ahead result.
    """
    eligible = forecasts[
        forecasts["publishTime"] <= forecasts["startTime"]
    ].copy()

    eligible = eligible.sort_values("publishTime")

    selected = eligible.drop_duplicates(
        subset=["startTime"],
        keep="last",
    )

    comparison = actuals.merge(
        selected[
            ["startTime", "publishTime", "forecast_generation"]
        ],
        on="startTime",
        how="inner",
        validate="one_to_one",
    )

    print_metrics("BASELINE FORECAST ACCURACY", comparison)

    print("\nBaseline coverage:")
    print("Hourly actual records:", len(actuals))
    print("Eligible forecast records:", len(eligible))
    print("Selected forecast records:", len(selected))
    print("Matched records:", len(comparison))
    print("Hours without a forecast:", len(actuals) - len(comparison))

    output_file = DATA_DIR / "forecast_accuracy_baseline_january_2026.csv"

    comparison.to_csv(output_file, index=False)

    print("Baseline results saved to:", output_file.resolve())

    return comparison


# --------------------------------------------------
# Day-ahead evaluation
# --------------------------------------------------

def evaluate_day_ahead(actuals, forecasts):
    """
    Select the latest forecast available by the configured
    cutoff on the day before each delivery date.

    The cutoff is an explicit assessment assumption, not
    an official procurement deadline.
    """
    print("\n" + "=" * 55)
    print("DAY-AHEAD FORECAST EVALUATION")
    print("=" * 55)

    print(
        "Decision-time assumption: latest forecast published "
        f"by {DECISION_CUTOFF_HOUR_UTC:02d}:00 UTC "
        "on the previous calendar day."
    )

    delivery_hours = actuals.copy()

    delivery_hours["decision_cutoff"] = (
        delivery_hours["startTime"].dt.normalize()
        - pd.Timedelta(days=1)
        + pd.Timedelta(hours=DECISION_CUTOFF_HOUR_UTC)
    )

    # Attach each forecast to the actual delivery hour.
    candidates = delivery_hours[
        ["startTime", "actual_generation", "decision_cutoff"]
    ].merge(
        forecasts[
            ["startTime", "publishTime", "forecast_generation"]
        ],
        on="startTime",
        how="left",
    )

    # Exclude forecasts published after the decision cutoff.
    eligible = candidates[
        candidates["publishTime"].notna()
        & (
            candidates["publishTime"]
            <= candidates["decision_cutoff"]
        )
    ].copy()

    # For each delivery hour, retain the latest eligible forecast.
    eligible = eligible.sort_values("publishTime")

    selected = eligible.drop_duplicates(
        subset=["startTime"],
        keep="last",
    ).copy()

    selected = selected.sort_values("startTime")

    selected["forecast_error"] = (
        selected["forecast_generation"]
        - selected["actual_generation"]
    )

    selected["absolute_error"] = (
        selected["forecast_error"].abs()
    )

    selected["absolute_percentage_error"] = np.where(
        selected["actual_generation"] != 0,
        selected["absolute_error"]
        / selected["actual_generation"].abs()
        * 100,
        np.nan,
    )

    print_metrics("DAY-AHEAD ACCURACY METRICS", selected)

    missing_hours = len(actuals) - len(selected)

    print("\nDay-ahead coverage:")
    print("Total delivery hours:", len(actuals))
    print("Eligible forecast records:", len(eligible))
    print("Delivery hours with a selected forecast:", len(selected))
    print("Delivery hours without an eligible forecast:", missing_hours)

    if not selected.empty:
        lead_times = (
            selected["startTime"] - selected["publishTime"]
        ).dt.total_seconds() / 3600

        print("\nForecast lead time:")
        print("Minimum hours:", round(float(lead_times.min()), 2))
        print("Median hours:", round(float(lead_times.median()), 2))
        print("Maximum hours:", round(float(lead_times.max()), 2))

    output_file = DATA_DIR / "forecast_accuracy_day_ahead_january_2026.csv"

    selected.to_csv(output_file, index=False)

    print("\nDay-ahead results saved to:", output_file.resolve())

    return selected


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    print("Loading January 2026 wind data...")

    actuals = load_actuals()
    forecasts = load_forecasts()

    print("\nData loaded successfully.")
    print("Hourly actual records:", len(actuals))
    print("Forecast records:", len(forecasts))

    inspect_publication_schedule(forecasts)

    evaluate_baseline(actuals, forecasts)

    evaluate_day_ahead(actuals, forecasts)

    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
