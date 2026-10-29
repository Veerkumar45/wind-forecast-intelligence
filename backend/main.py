from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DAY_AHEAD_FILE = DATA_DIR / "forecast_accuracy_day_ahead_january_2026.csv"
BASELINE_FILE = DATA_DIR / "forecast_accuracy_baseline_january_2026.csv"
DAILY_FILE = DATA_DIR / "daily_forecast_accuracy_january_2026.csv"


# --------------------------------------------------
# Application
# --------------------------------------------------

app = FastAPI(
    title="Wind Forecast Intelligence API",
    description=(
        "API for analyzing UK wind generation forecasts, "
        "forecast accuracy, and daily errors for January 2026."
    ),
    version="1.0.0",
)

# Allow the React frontend to access the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Data loading
# --------------------------------------------------

def load_csv(filename: Path) -> pd.DataFrame:
    """Load a CSV file or report a clear API error."""
    if not filename.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Required data file not found: {filename.name}",
        )

    try:
        return pd.read_csv(filename)
    except (OSError, pd.errors.ParserError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read {filename.name}: {error}",
        ) from error


def load_day_ahead() -> pd.DataFrame:
    """Load the selected day-ahead forecast comparisons."""
    data = load_csv(DAY_AHEAD_FILE)

    required_columns = {
        "startTime",
        "actual_generation",
        "forecast_generation",
    }

    if not required_columns.issubset(data.columns):
        raise HTTPException(
            status_code=500,
            detail="Day-ahead CSV is missing required columns.",
        )

    data["startTime"] = pd.to_datetime(
        data["startTime"],
        utc=True,
        errors="coerce",
    )

    for column in ["actual_generation", "forecast_generation"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    return data.dropna(
        subset=[
            "startTime",
            "actual_generation",
            "forecast_generation",
        ]
    ).copy()


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
def home():
    """API welcome message."""
    return {
        "message": "Wind Forecast Intelligence API is running.",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    """Check API and data-file availability."""
    files = {
        "day_ahead": DAY_AHEAD_FILE,
        "baseline": BASELINE_FILE,
        "daily": DAILY_FILE,
    }

    return {
        "status": "healthy",
        "data_files": {
            name: path.exists()
            for name, path in files.items()
        },
    }


@app.get("/api/summary")
def get_summary():
    """Return headline forecast accuracy metrics."""
    day_ahead = load_day_ahead()
    baseline = load_csv(BASELINE_FILE)

    if day_ahead.empty:
        raise HTTPException(
            status_code=500,
            detail="No valid day-ahead forecast records were found.",
        )

    actual = day_ahead["actual_generation"]
    forecast = day_ahead["forecast_generation"]
    errors = forecast - actual

    baseline_required = {
        "actual_generation",
        "forecast_generation",
    }

    if not baseline_required.issubset(baseline.columns):
        raise HTTPException(
            status_code=500,
            detail="Baseline CSV is missing required columns.",
        )

    baseline_actual = pd.to_numeric(
        baseline["actual_generation"],
        errors="coerce",
    )
    baseline_forecast = pd.to_numeric(
        baseline["forecast_generation"],
        errors="coerce",
    )

    valid_baseline = pd.DataFrame(
        {
            "actual": baseline_actual,
            "forecast": baseline_forecast,
        }
    ).dropna()

    baseline_errors = (
        valid_baseline["forecast"] - valid_baseline["actual"]
    )

    nonzero_actual = actual != 0
    mape = (
        (errors[nonzero_actual].abs() / actual[nonzero_actual].abs()).mean()
        * 100
        if nonzero_actual.any()
        else None
    )

    baseline_mae = (
        float(baseline_errors.abs().mean())
        if not baseline_errors.empty
        else None
    )

    return {
        "period": "January 2026",
        "forecast_type": "Day-ahead",
        "decision_cutoff": "12:00 UTC on the previous calendar day",
        "cutoff_is_assessment_assumption": True,
        "hours_evaluated": int(len(day_ahead)),
        "mae": round(float(errors.abs().mean()), 2),
        "rmse": round(float((errors.pow(2).mean()) ** 0.5), 2),
        "forecast_bias": round(float(errors.mean()), 2),
        "mape_percent": round(float(mape), 2) if mape is not None else None,
        "baseline_mae": (
            round(baseline_mae, 2)
            if baseline_mae is not None
            else None
        ),
    }


@app.get("/api/daily-accuracy")
def get_daily_accuracy():
    """Return daily forecast accuracy for charts."""
    daily = load_csv(DAILY_FILE)

    required_columns = {
        "delivery_date",
        "hours_evaluated",
        "MAE",
        "RMSE",
        "forecast_bias",
        "MAPE_percent",
    }

    if not required_columns.issubset(daily.columns):
        raise HTTPException(
            status_code=500,
            detail="Daily accuracy CSV is missing required columns.",
        )

    daily = daily.sort_values("delivery_date")

    return {
        "period": "January 2026",
        "days_evaluated": int(len(daily)),
        "results": daily.where(pd.notna(daily), None).to_dict(
            orient="records"
        ),
    }


@app.get("/api/hourly-comparison")
def get_hourly_comparison(
    start_date: str = "2026-01-01",
    end_date: str = "2026-01-31",
):
    """Return actual and forecast generation for a date range."""
    try:
        start = pd.Timestamp(start_date, tz="UTC")
        end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=400,
            detail="Dates must use YYYY-MM-DD format.",
        ) from error

    if start >= end:
        raise HTTPException(
            status_code=400,
            detail="start_date must be earlier than or equal to end_date.",
        )

    data = load_day_ahead()

    data = data[
        (data["startTime"] >= start)
        & (data["startTime"] < end)
    ].sort_values("startTime")

    results = []

    for _, row in data.iterrows():
        actual = float(row["actual_generation"])
        forecast = float(row["forecast_generation"])

        results.append(
            {
                "timestamp": row["startTime"].isoformat(),
                "actual_generation": actual,
                "forecast_generation": forecast,
                "error": round(forecast - actual, 2),
                "absolute_error": round(abs(forecast - actual), 2),
            }
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "hours_returned": len(results),
        "results": results,
    }


@app.get("/api/worst-days")
def get_worst_days(limit: int = 5):
    """Return days with the highest mean absolute error."""
    if limit < 1 or limit > 31:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 31.",
        )

    daily = load_csv(DAILY_FILE)

    if not {"delivery_date", "MAE", "RMSE", "forecast_bias"}.issubset(
        daily.columns
    ):
        raise HTTPException(
            status_code=500,
            detail="Daily accuracy CSV is missing required columns.",
        )

    worst = daily.nlargest(limit, "MAE")

    return {
        "description": "Days ranked by highest mean absolute forecast error.",
        "results": worst.where(pd.notna(worst), None).to_dict(
            orient="records"
        ),
    }


@app.get("/api/forecast-bias")
def get_forecast_bias():
    """Summarize overforecasting and underforecasting."""
    data = load_day_ahead()
    errors = data["forecast_generation"] - data["actual_generation"]

    overforecast_hours = int((errors > 0).sum())
    underforecast_hours = int((errors < 0).sum())
    exact_hours = int((errors == 0).sum())

    return {
        "hours_evaluated": int(len(errors)),
        "overforecast_hours": overforecast_hours,
        "underforecast_hours": underforecast_hours,
        "exact_forecast_hours": exact_hours,
        "mean_forecast_bias": round(float(errors.mean()), 2),
        "interpretation": (
            "Positive bias means forecasts exceed actual generation; "
            "negative bias means forecasts are below actual generation."
        ),
    }
