"""FastAPI application for the local OceanSense AI web client."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
import secrets
from threading import Lock
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.src.interactive import posterior_prediction_for_date, validate_uploaded_csv
from backend.src.model import (
    NPZDParameters,
    load_observations,
    posterior_predictive,
    posterior_summary,
    run_bayesian_estimation,
    sampling_diagnostics,
    simulate_npzd,
)


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
BUNDLED_OBSERVATIONS = load_observations()
BUNDLED_POSTERIOR = pd.read_csv(PROCESSED / "posterior_samples.csv")
BUNDLED_PREDICTIVE = pd.read_csv(PROCESSED / "posterior_predictive.csv")
BUNDLED_DIAGNOSTICS = pd.read_csv(PROCESSED / "posterior_diagnostics.csv")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_ROWS = 10_000
MAX_STORED_UPLOADS = 32
uploaded_datasets: dict[str, pd.DataFrame] = {}
upload_lock = Lock()
estimation_lock = Lock()
runtime_posterior: pd.DataFrame | None = None
runtime_predictive: pd.DataFrame | None = None
runtime_diagnostics: pd.DataFrame | None = None
runtime_acceptance: float | None = None

app = FastAPI(
    title="OceanSense AI API",
    description="Local API for bundled Black Sea observations and the existing NPZD/Bayesian model.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    dataset: Literal["bundled", "uploaded"] = "bundled"
    target_date: date
    upload_id: str | None = None


def _records(frame: pd.DataFrame) -> list[dict]:
    result = frame.copy()
    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    result = result.replace({np.nan: None})
    return result.to_dict(orient="records")


def _current_posterior() -> pd.DataFrame:
    return runtime_posterior if runtime_posterior is not None else BUNDLED_POSTERIOR


def _current_predictive() -> pd.DataFrame:
    return runtime_predictive if runtime_predictive is not None else BUNDLED_PREDICTIVE


def _current_diagnostics() -> pd.DataFrame:
    return runtime_diagnostics if runtime_diagnostics is not None else BUNDLED_DIAGNOSTICS


def _posterior_payload() -> dict:
    posterior = _current_posterior()
    diagnostics = _current_diagnostics()
    summary = posterior_summary(posterior)
    acceptance = (
        runtime_acceptance
        if runtime_acceptance is not None
        else float(BUNDLED_DIAGNOSTICS["mean_acceptance_rate"].iloc[0])
    )
    return {
        "draw_count": int(len(posterior)),
        "parameter_count": int(len(posterior.columns)),
        "mean_acceptance_rate": acceptance,
        "parameters": _records(summary),
        "diagnostics": _records(diagnostics),
        "fresh_estimate": runtime_posterior is not None,
    }


def _get_uploaded(upload_id: str | None) -> pd.DataFrame:
    if not upload_id:
        raise HTTPException(status_code=422, detail="An upload_id is required for the uploaded dataset.")
    with upload_lock:
        dataset = uploaded_datasets.get(upload_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="This uploaded dataset is no longer available. Upload it again.")
    return dataset.copy()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "OceanSense AI API"}


@app.get("/api/observations")
def observations() -> dict:
    return {"count": len(BUNDLED_OBSERVATIONS), "rows": _records(BUNDLED_OBSERVATIONS)}


@app.get("/api/metadata")
def metadata() -> dict:
    data = BUNDLED_OBSERVATIONS
    return {
        "observation_count": len(data),
        "start_date": data["date"].min().date().isoformat(),
        "end_date": data["date"].max().date().isoformat(),
        "chlorophyll_range_mg_m3": [
            float(data["chlorophyll_mg_m3"].min()),
            float(data["chlorophyll_mg_m3"].max()),
        ],
        "chlorophyll_mean_mg_m3": float(data["chlorophyll_mg_m3"].mean()),
        "chlorophyll_valid_pixels_range": [
            int(data["chlorophyll_valid_pixels"].min()),
            int(data["chlorophyll_valid_pixels"].max()),
        ],
        "mean_chlorophyll_valid_pixels": float(data["chlorophyll_valid_pixels"].mean()),
        "sst_range_c": [float(data["sst_c"].min()), float(data["sst_c"].max())],
        "sst_mean_c": float(data["sst_c"].mean()),
        "sst_min_date": data.loc[data["sst_c"].idxmin(), "date"].date().isoformat(),
        "sst_max_date": data.loc[data["sst_c"].idxmax(), "date"].date().isoformat(),
        "chlorophyll_source": "JRC EMIS Black Sea MODIS-Aqua",
        "sst_source": "NOAA OISST v2.1 Level-4 analysis",
        "offline": True,
        "limitations": [
            "The bundled dataset contains 11 paired observation dates from 2003; September is absent.",
            "Mixed-layer depth and PAR are not bundled observations; seasonal light is a model assumption.",
            "Predictions are conditional on a simplified NPZD model and do not represent future forecasts.",
            "Prediction intervals propagate parameter uncertainty only, not retrieval or structural model uncertainty.",
        ],
    }


@app.get("/api/model-info")
def model_info() -> dict:
    return {
        "name": "Simplified NPZD ecosystem model",
        "states": [
            {"key": "nutrient", "label": "Nutrient", "unit": "relative units"},
            {"key": "phytoplankton", "label": "Phytoplankton", "unit": "relative units"},
            {"key": "zooplankton", "label": "Zooplankton", "unit": "relative units"},
            {"key": "detritus", "label": "Detritus", "unit": "relative units"},
        ],
        "default_parameters": asdict(NPZDParameters()),
        "temperature_forcing": "Bundled SST observations",
        "light_forcing": "Dimensionless seasonal assumption; not measured PAR",
        "bayesian_method": "Random-walk Metropolis-Hastings in log-parameter space",
        "posterior_parameters": list(_current_posterior().columns),
    }


@app.get("/api/npzd")
def npzd_simulation(days: int = 365) -> dict:
    if days < 1 or days > 3650:
        raise HTTPException(status_code=422, detail="days must be between 1 and 3650.")
    simulation = simulate_npzd(observations=BUNDLED_OBSERVATIONS, days=days)
    return {"count": len(simulation), "rows": _records(simulation)}


@app.get("/api/posterior")
def posterior() -> dict:
    return _posterior_payload()


@app.get("/api/posterior/distribution/{parameter}")
def posterior_distribution(parameter: str) -> dict:
    posterior_samples = _current_posterior()
    if parameter not in posterior_samples.columns:
        raise HTTPException(status_code=404, detail=f"Unknown posterior parameter: {parameter}.")
    values = posterior_samples[parameter].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise HTTPException(status_code=500, detail="Posterior samples contain non-finite values.")
    counts, edges = np.histogram(values, bins=40, density=True)
    summary = posterior_summary(posterior_samples).set_index("parameter").loc[parameter]
    bins = [
        {
            "x": float((edges[index] + edges[index + 1]) / 2),
            "density": float(counts[index]),
        }
        for index in range(len(counts))
    ]
    return {
        "parameter": parameter,
        "bins": bins,
        "median": float(summary["median"]),
        "credible_interval_2_5": float(summary["credible_interval_2_5"]),
        "credible_interval_97_5": float(summary["credible_interval_97_5"]),
    }


@app.post("/api/bayesian/estimate")
def estimate_posterior() -> dict:
    global runtime_posterior, runtime_predictive, runtime_diagnostics, runtime_acceptance

    if not estimation_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A Bayesian estimation is already running.")
    try:
        samples, acceptance = run_bayesian_estimation(
            BUNDLED_OBSERVATIONS,
            draws=1200,
            burn_in=300,
            seed=2026,
            chains=4,
        )
        diagnostics = sampling_diagnostics(samples)
        predictive = posterior_predictive(samples, BUNDLED_OBSERVATIONS, samples=100)
        runtime_posterior = samples
        runtime_predictive = predictive
        runtime_diagnostics = diagnostics
        runtime_acceptance = acceptance
        return _posterior_payload()
    finally:
        estimation_lock.release()


@app.get("/api/prediction-uncertainty")
def prediction_uncertainty() -> dict:
    return {"rows": _records(_current_predictive())}


@app.post("/api/uploads")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    if not file.filename or Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=415, detail="Upload a .csv observation file.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV uploads must be 5 MB or smaller.")
    try:
        data = validate_uploaded_csv(content)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if len(data) > MAX_UPLOAD_ROWS:
        raise HTTPException(status_code=422, detail=f"CSV uploads may contain at most {MAX_UPLOAD_ROWS:,} rows.")

    upload_id = secrets.token_urlsafe(24)
    with upload_lock:
        if len(uploaded_datasets) >= MAX_STORED_UPLOADS:
            oldest_id = next(iter(uploaded_datasets))
            del uploaded_datasets[oldest_id]
        uploaded_datasets[upload_id] = data
    return {
        "upload_id": upload_id,
        "filename": Path(file.filename).name,
        "count": len(data),
        "rows": _records(data),
    }


@app.get("/api/uploads/{upload_id}")
def get_uploaded_dataset(upload_id: str) -> dict:
    data = _get_uploaded(upload_id)
    return {"count": len(data), "rows": _records(data)}


@app.delete("/api/uploads/{upload_id}")
def delete_uploaded_dataset(upload_id: str) -> dict:
    with upload_lock:
        if uploaded_datasets.pop(upload_id, None) is None:
            raise HTTPException(status_code=404, detail="Uploaded dataset not found.")
    return {"deleted": True}


@app.post("/api/predictions")
def predict(request: PredictionRequest) -> dict:
    if request.dataset == "bundled":
        data = BUNDLED_OBSERVATIONS.copy()
    else:
        data = _get_uploaded(request.upload_id)

    target = pd.Timestamp(request.target_date)
    try:
        prediction = posterior_prediction_for_date(_current_posterior(), data, target)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    matching = data.loc[pd.to_datetime(data["date"]).dt.normalize() == target.normalize()]
    observation = matching.iloc[0] if not matching.empty else None
    return {
        "dataset": request.dataset,
        "target_date": target.date().isoformat(),
        "observed_sst_c": float(observation["sst_c"]) if observation is not None else None,
        "observed_chlorophyll_mg_m3": (
            float(observation["chlorophyll_mg_m3"]) if observation is not None else None
        ),
        **prediction,
        "interval_scope": "parameter uncertainty only",
        "is_future_forecast": False,
    }
