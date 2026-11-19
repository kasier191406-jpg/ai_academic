from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from src.data_pipeline import build_processed_observations
from src.model import (
    NPZDParameters,
    _derivative,
    load_observations,
    posterior_predictive,
    posterior_summary,
    run_bayesian_estimation,
    sampling_diagnostics,
    simulate_npzd,
)


def test_bundled_observations_are_real_and_loadable():
    data = load_observations()
    assert len(data) == 11
    assert data["date"].min().year == 2003
    assert (data["chlorophyll_mg_m3"] > 0).all()
    assert (data["sst_c"] > 0).all()
    assert (data["chlorophyll_valid_pixels"] > 0).all()
    for filename in data["chlorophyll_source_file"]:
        assert (Path("data/raw/chlorophyll") / filename).exists()
    for filename in data["sst_source_file"]:
        assert (Path("data/raw/sst") / filename).exists()


def test_raw_netcdf_variables_units_coordinates_and_dates():
    with xr.open_dataset("data/raw/chlorophyll/EMIS_D_chlideachla2003015_MODIS_EUR_BLCK.nc") as chl:
        assert chl["chlideachla"].attrs["units"] == "mg/m-3"
        assert chl["lat"].min().item() == 40.75
        assert chl["lat"].max().item() > 47.4
        assert np.isfinite(chl["chlideachla"].values).sum() == 569

    with xr.open_dataset("data/raw/sst/sst_20030115.nc") as sst:
        assert sst["sst"].attrs["units"] == "Celsius"
        assert pd.Timestamp(sst["time"].values[0]).date() == pd.Timestamp("2003-01-15").date()
        regional = sst["sst"].sel(lat=slice(40.5, 48.0), lon=slice(27.0, 42.0))
        assert np.isfinite(regional.values).any()


def test_pipeline_rebuilds_processed_file():
    rebuilt = build_processed_observations()
    assert len(rebuilt) == 11
    assert Path("data/processed/black_sea_observations_2003.csv").exists()


def test_npzd_states_are_finite_and_nonnegative():
    simulation = simulate_npzd(observations=load_observations())
    assert len(simulation) == 366
    assert np.isfinite(simulation[["nutrient", "phytoplankton", "zooplankton", "detritus"]].to_numpy()).all()
    assert (simulation[["nutrient", "phytoplankton", "zooplankton", "detritus"]].to_numpy() >= 0).all()


def test_npzd_transfers_conserve_mass_except_detritus_sinking():
    parameters = NPZDParameters()
    state = np.array([1.2, 0.25, 0.12, 0.20])
    derivative = _derivative(state, 100, 15, parameters)
    expected_loss = -parameters.detritus_sinking_rate * state[3]
    assert np.isclose(derivative.sum(), expected_loss)


def test_mcmc_returns_posterior_and_predictive_intervals():
    data = load_observations()
    posterior, acceptance = run_bayesian_estimation(data, draws=180, burn_in=60, seed=7, chains=2)
    assert len(posterior) == 240
    assert 0 < acceptance < 1
    assert posterior.attrs["chain_samples"].shape == (2, 120, 5)
    bounds = {
        "growth_rate_day": (0.01, 4),
        "grazing_rate_day": (0.005, 3),
        "zooplankton_mortality_day": (0.002, 2),
        "chlorophyll_scale_mg_m3": (0.05, 100),
        "observation_log_sd": (0.03, 3),
    }
    for parameter, (lower, upper) in bounds.items():
        assert ((posterior[parameter] > lower) & (posterior[parameter] < upper)).all()
    summary = posterior_summary(posterior)
    assert (summary["credible_interval_97_5"] > summary["credible_interval_2_5"]).all()
    diagnostics = sampling_diagnostics(posterior)
    assert np.isfinite(diagnostics["split_rhat"]).all()
    assert (diagnostics["effective_sample_size"] > 0).all()
    prediction = posterior_predictive(posterior, data, samples=20, seed=7)
    assert (prediction["upper_95"] >= prediction["lower_95"]).all()
