
import pandas as pd
import numpy as np
from pathlib import Path


DATA_DIR = Path("data")

INPUT_FILE = DATA_DIR / "forecast_accuracy_day_ahead_january_2026.csv"
OUTPUT_FILE = DATA_DIR / "daily_forecast_accuracy_january_2026.csv"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_FILE}. "
            "Run analyze_forecast_accuracy.py first."
        )

    data = pd.read_csv(INPUT_FILE)

    data["startTime"] = pd.to_datetime(
        data["startTime"],
        utc=True,
    )

    data["actual_generation"] = pd.to_numeric(
        data["actual_generation"],
        errors="coerce",
    )

    data["forecast_generation"] = pd.to_numeric(
        data["forecast_generation"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "startTime",
            "actual_generation",
            "forecast_generation",
        ]
    ).copy()

    # Group delivery hours by UTC calendar day.
    data["delivery_date"] = (
        data["startTime"].dt.strftime("%Y-%m-%d")
    )

    data["forecast_error"] = (
        data["forecast_generation"]
        - data["actual_generation"]
    )

    data["absolute_error"] = data["forecast_error"].abs()

    data["squared_error"] = data["forecast_error"] ** 2

    data["absolute_percentage_error"] = np.where(
        data["actual_generation"] != 0,
        data["absolute_error"]
        / data["actual_generation"].abs()
        * 100,
        np.nan,
    )

    daily = (
        data.groupby("delivery_date")
        .agg(
            hours_evaluated=("startTime", "count"),
            actual_generation_mean=("actual_generation", "mean"),
            forecast_generation_mean=("forecast_generation", "mean"),
            MAE=("absolute_error", "mean"),
            mean_squared_error=("squared_error", "mean"),
            forecast_bias=("forecast_error", "mean"),
            MAPE_percent=("absolute_percentage_error", "mean"),
        )
        .reset_index()
    )

    daily["RMSE"] = np.sqrt(daily["mean_squared_error"])

    daily = daily.drop(columns=["mean_squared_error"])

    numeric_columns = [
        "actual_generation_mean",
        "forecast_generation_mean",
        "MAE",
        "RMSE",
        "forecast_bias",
        "MAPE_percent",
    ]

    daily[numeric_columns] = daily[numeric_columns].round(2)

    daily.to_csv(OUTPUT_FILE, index=False)

    print("\n=== DAILY FORECAST ACCURACY ===")
    print("Days evaluated:", len(daily))
    print("Hours evaluated:", int(daily["hours_evaluated"].sum()))

    print("\nFive days with the highest MAE:")
    print(
        daily.nlargest(5, "MAE")[
            [
                "delivery_date",
                "hours_evaluated",
                "MAE",
                "RMSE",
                "forecast_bias",
            ]
        ].to_string(index=False)
    )

    print("\nFive days with the lowest MAE:")
    print(
        daily.nsmallest(5, "MAE")[
            [
                "delivery_date",
                "hours_evaluated",
                "MAE",
                "RMSE",
                "forecast_bias",
            ]
        ].to_string(index=False)
    )

    print("\nSaved daily results to:")
    print(OUTPUT_FILE.resolve())


if __name__ == "__main__":
    main()
