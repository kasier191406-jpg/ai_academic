"""CSV validation and date-specific access to the existing model prediction."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd

from backend.src.model import posterior_predictive

UPLOAD_COLUMNS = ("date", "sst_c", "chlorophyll_mg_m3")


def validate_uploaded_csv(content: bytes) -> pd.DataFrame:
    """Return validated, sorted upload observations without touching bundled data."""
    try:
        frame = pd.read_csv(BytesIO(content))
    except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise ValueError(f"Could not read the CSV file: {error}") from error

    missing_columns = set(UPLOAD_COLUMNS).difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing_columns))}.")
    if frame.empty:
        raise ValueError("The CSV must contain at least one observation row.")

    frame = frame.loc[:, list(UPLOAD_COLUMNS)].copy()
    missing_values = frame.isna().any()
    if missing_values.any():
        columns = ", ".join(missing_values[missing_values].index)
        raise ValueError(f"Missing values are not allowed in: {columns}.")

    if not frame["date"].map(lambda value: isinstance(value, str)).all():
        raise ValueError("The date column must contain date strings.")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("The date column contains invalid dates.")
    try:
        if dates.dt.tz is not None:
            raise ValueError("Dates must use a timezone-free format.")
        frame["date"] = dates.dt.normalize()
    except AttributeError as error:
        raise ValueError("Dates must use a consistent timezone-free format.") from error

    for column in ("sst_c", "chlorophyll_mg_m3"):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.isna().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise ValueError(f"The {column} column must contain finite numerical values.")
        frame[column] = numeric.astype(float)

    if (frame["chlorophyll_mg_m3"] < 0).any():
        raise ValueError("Chlorophyll-a values cannot be negative.")
    if frame["date"].duplicated().any():
        raise ValueError("Each observation date must be unique.")

    return frame.sort_values("date").reset_index(drop=True)


def posterior_prediction_for_date(
    posterior: pd.DataFrame,
    observations: pd.DataFrame,
    target_date: pd.Timestamp,
) -> dict[str, float]:
    """Extract a model estimate using that calendar year's SST forcing only."""
    if posterior.empty:
        raise ValueError("The bundled Bayesian posterior contains no parameter samples.")

    target = pd.Timestamp(target_date).normalize()
    year_observations = observations.loc[
        pd.to_datetime(observations["date"]).dt.year == target.year,
        ["date", "sst_c"],
    ].copy()
    year_observations["date"] = pd.to_datetime(year_observations["date"])
    year_observations = year_observations.sort_values("date")

    if len(year_observations) < 2:
        raise ValueError(
            "At least two SST observations in the selected calendar year are needed "
            "to provide interpolated model forcing."
        )
    if not year_observations["date"].min() <= target <= year_observations["date"].max():
        raise ValueError(
            "The selected date must fall within the available SST observation dates "
            "for its calendar year."
        )

    day = (target - pd.Timestamp(target.year, 1, 1)).days
    trajectory = posterior_predictive(
        posterior,
        observations=year_observations,
        samples=min(150, len(posterior)),
        seed=9,
    )
    selected = trajectory.loc[trajectory["day"] == day]
    if selected.empty:
        raise ValueError("The existing model does not provide a prediction for this date.")

    row = selected.iloc[0]
    result = {
        "median": float(row["median_chlorophyll_mg_m3"]),
        "lower_95": float(row["lower_95"]),
        "upper_95": float(row["upper_95"]),
    }
    if (
        not np.isfinite(list(result.values())).all()
        or result["lower_95"] > result["median"]
        or result["median"] > result["upper_95"]
    ):
        raise ValueError("The existing model returned an invalid prediction interval.")
    return result
