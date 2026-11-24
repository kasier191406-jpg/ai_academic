"""Numerical NPZD model and Metropolis-Hastings Bayesian calibration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "processed" / "black_sea_observations_2003.csv"


@dataclass(frozen=True)
class NPZDParameters:
    growth_rate: float = 0.75
    half_saturation: float = 0.45
    grazing_rate: float = 0.38
    zooplankton_mortality: float = 0.11
    phytoplankton_mortality: float = 0.045
    assimilation_efficiency: float = 0.65
    remineralization_rate: float = 0.08
    detritus_sinking_rate: float = 0.025


def load_observations() -> pd.DataFrame:
    """Load only the bundled processed observations."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Bundled data missing: {DATA_FILE}")
    observations = pd.read_csv(DATA_FILE, parse_dates=["date"])
    required = {"date", "chlorophyll_mg_m3", "sst_c", "chlorophyll_valid_pixels"}
    missing = required.difference(observations.columns)
    if missing:
        raise ValueError(f"Bundled observations missing columns: {sorted(missing)}")
    return observations.sort_values("date").reset_index(drop=True)


def seasonal_light_factor(day: float) -> float:
    """Dimensionless seasonal light forcing used by the simplified model."""
    return float(np.clip(0.60 + 0.40 * np.sin(2 * np.pi * (day - 80) / 365), 0.12, 1.0))


def _derivative(state: np.ndarray, day: float, temperature_c: float, parameters: NPZDParameters) -> np.ndarray:
    nutrient, phytoplankton, zooplankton, detritus = np.maximum(state, 1e-10)
    temperature_factor = np.exp(0.063 * (temperature_c - 15.0))
    production = parameters.growth_rate * temperature_factor * seasonal_light_factor(day) * nutrient / (parameters.half_saturation + nutrient) * phytoplankton
    grazing = parameters.grazing_rate * phytoplankton / (0.30 + phytoplankton) * zooplankton
    phy_loss = parameters.phytoplankton_mortality * phytoplankton
    zoo_loss = parameters.zooplankton_mortality * zooplankton**2
    remineralization = parameters.remineralization_rate * detritus
    return np.array([
        -production + remineralization,
        production - grazing - phy_loss,
        parameters.assimilation_efficiency * grazing - zoo_loss,
        phy_loss + (1 - parameters.assimilation_efficiency) * grazing + zoo_loss - remineralization - parameters.detritus_sinking_rate * detritus,
    ])


def daily_sst(observations: pd.DataFrame, days: int = 365) -> np.ndarray:
    reference = pd.Timestamp(observations["date"].min().year, 1, 1)
    observation_days = (observations["date"] - reference).dt.days.to_numpy()
    return np.interp(np.arange(days + 1), observation_days, observations["sst_c"].to_numpy())


def simulate_npzd(parameters: NPZDParameters = NPZDParameters(), observations: pd.DataFrame | None = None, days: int = 365, initial_state: tuple[float, float, float, float] = (1.2, 0.25, 0.12, 0.20)) -> pd.DataFrame:
    """Integrate NPZD equations with fourth-order Runge-Kutta daily stepping."""
    if observations is None:
        observations = load_observations()
    temperatures = daily_sst(observations, days)
    states = np.empty((days + 1, 4), dtype=float)
    states[0] = initial_state
    for day in range(days):
        state = states[day]
        temperature = temperatures[day]
        k1 = _derivative(state, day, temperature, parameters)
        k2 = _derivative(state + 0.5 * k1, day + 0.5, temperature, parameters)
        k3 = _derivative(state + 0.5 * k2, day + 0.5, temperature, parameters)
        k4 = _derivative(state + k3, day + 1, temperature, parameters)
        states[day + 1] = np.maximum(state + (k1 + 2 * k2 + 2 * k3 + k4) / 6, 1e-9)
    return pd.DataFrame({"day": np.arange(days + 1), "sst_c": temperatures, "nutrient": states[:, 0], "phytoplankton": states[:, 1], "zooplankton": states[:, 2], "detritus": states[:, 3]})


PARAMETER_NAMES = ["growth_rate_day", "grazing_rate_day", "zooplankton_mortality_day", "chlorophyll_scale_mg_m3", "observation_log_sd"]


def _to_parameters(theta: np.ndarray) -> tuple[NPZDParameters, float, float]:
    values = np.exp(theta)
    return NPZDParameters(growth_rate=values[0], grazing_rate=values[1], zooplankton_mortality=values[2]), float(values[3]), float(values[4])


def _log_posterior(theta: np.ndarray, observations: pd.DataFrame) -> float:
    log_lower = np.log([0.01, 0.005, 0.002, 0.05, 0.03])
    log_upper = np.log([4.0, 3.0, 2.0, 100.0, 3.0])
    if not np.isfinite(theta).all() or np.any(theta <= log_lower) or np.any(theta >= log_upper):
        return -np.inf
    prior_means = np.log([0.75, 0.38, 0.11, 5.0, 0.45])
    prior_sds = np.array([0.55, 0.55, 0.60, 1.0, 0.50])
    log_prior = -0.5 * np.sum(((theta - prior_means) / prior_sds) ** 2)
    parameters, scale, sigma = _to_parameters(theta)
    simulation = simulate_npzd(parameters, observations)
    if not np.isfinite(simulation["phytoplankton"].to_numpy()).all():
        return -np.inf
    reference = pd.Timestamp(observations["date"].min().year, 1, 1)
    sample_days = (observations["date"] - reference).dt.days.to_numpy()
    expected = np.interp(sample_days, simulation["day"], simulation["phytoplankton"]) * scale
    residuals = np.log(observations["chlorophyll_mg_m3"].to_numpy()) - np.log(np.maximum(expected, 1e-12))
    if not np.isfinite(residuals).all():
        return -np.inf
    log_likelihood = -np.sum(np.log(sigma) + 0.5 * np.log(2 * np.pi) + residuals**2 / (2 * sigma**2))
    return float(log_prior + log_likelihood)


def run_bayesian_estimation(observations: pd.DataFrame | None = None, draws: int = 5000, burn_in: int = 1500, seed: int = 2026, chains: int = 1) -> tuple[pd.DataFrame, float]:
    """Sample the posterior using random-walk Metropolis-Hastings MCMC."""
    if observations is None:
        observations = load_observations()
    if draws <= burn_in or burn_in < 0:
        raise ValueError("draws must be greater than a non-negative burn_in")
    if chains < 1:
        raise ValueError("chains must be at least one")
    prior_means = np.log([0.75, 0.38, 0.11, 5.0, 0.45])
    log_lower = np.log([0.01, 0.005, 0.002, 0.05, 0.03])
    log_upper = np.log([4.0, 3.0, 2.0, 100.0, 3.0])
    proposal_scale = np.array([0.45, 0.45, 0.45, 0.375, 0.30])
    chain_samples = np.empty((chains, draws - burn_in, len(prior_means)))
    acceptance_rates = np.empty(chains)
    random_generators = np.random.SeedSequence(seed).spawn(chains)
    for chain_index, child_seed in enumerate(random_generators):
        rng = np.random.default_rng(child_seed)
        current = np.clip(prior_means + rng.normal(0, 0.15, len(prior_means)), log_lower + 1e-8, log_upper - 1e-8)
        current_log_posterior = _log_posterior(current, observations)
        chain = np.empty((draws, len(current)))
        accepted = 0
        for index in range(draws):
            candidate = current + rng.normal(0, proposal_scale)
            candidate_log_posterior = _log_posterior(candidate, observations)
            if np.log(rng.random()) < candidate_log_posterior - current_log_posterior:
                current, current_log_posterior = candidate, candidate_log_posterior
                accepted += 1
            chain[index] = current
        chain_samples[chain_index] = np.exp(chain[burn_in:])
        acceptance_rates[chain_index] = accepted / draws
    posterior = pd.DataFrame(chain_samples.reshape(-1, len(PARAMETER_NAMES)), columns=PARAMETER_NAMES)
    posterior.attrs["chain_samples"] = chain_samples
    posterior.attrs["acceptance_rates"] = acceptance_rates
    posterior.attrs["draws_per_chain"] = draws - burn_in
    return posterior, float(acceptance_rates.mean())


def sampling_diagnostics(posterior: pd.DataFrame) -> pd.DataFrame:
    """Return autocorrelation ESS and split R-hat when multiple chains are available."""
    chain_samples = posterior.attrs.get("chain_samples")
    if chain_samples is None:
        chains = posterior.to_numpy(dtype=float)[None, :, :]
    else:
        chains = np.asarray(chain_samples, dtype=float)
    if chains.ndim != 3 or chains.shape[1] < 4 or not np.isfinite(chains).all():
        raise ValueError("Posterior diagnostics require at least four finite draws per chain.")

    chain_count, draw_count, parameter_count = chains.shape
    means = chains.mean(axis=1)
    within_variance = chains.var(axis=1, ddof=1).mean(axis=0)
    between_variance = draw_count * means.var(axis=0, ddof=1) if chain_count > 1 else np.zeros(parameter_count)
    variance_estimate = ((draw_count - 1) / draw_count) * within_variance + between_variance / draw_count
    split_rhat = np.full(parameter_count, np.nan)
    if chain_count > 1:
        half = draw_count // 2
        split_chains = np.concatenate((chains[:, :half, :], chains[:, -half:, :]), axis=0)
        split_count, split_draw_count, _ = split_chains.shape
        split_within = split_chains.var(axis=1, ddof=1).mean(axis=0)
        split_between = split_draw_count * split_chains.mean(axis=1).var(axis=0, ddof=1)
        split_variance = ((split_draw_count - 1) / split_draw_count) * split_within + split_between / split_draw_count
        split_rhat = np.sqrt(np.divide(split_variance, split_within, out=np.ones_like(split_variance), where=split_within > 0))

    effective_sample_size = np.empty(parameter_count)
    for parameter_index in range(parameter_count):
        within = within_variance[parameter_index]
        if within == 0:
            effective_sample_size[parameter_index] = chain_count * draw_count
            continue
        variance = max(variance_estimate[parameter_index], within)
        autocovariance = np.zeros(draw_count)
        for chain_index in range(chain_count):
            centered = chains[chain_index, :, parameter_index] - means[chain_index, parameter_index]
            autocovariance += np.correlate(centered, centered, mode="full")[draw_count - 1:] / draw_count
        autocovariance /= chain_count
        rho = 1 - (within - autocovariance) / variance
        paired_sum = 0.0
        previous_pair = np.inf
        for lag in range(1, draw_count - 1, 2):
            pair = rho[lag] + rho[lag + 1]
            if pair <= 0:
                break
            pair = min(pair, previous_pair)
            paired_sum += pair
            previous_pair = pair
        total = chain_count * draw_count
        effective_sample_size[parameter_index] = min(total, max(1.0, total / (1 + 2 * paired_sum)))

    diagnostics = pd.DataFrame({
        "parameter": posterior.columns,
        "effective_sample_size": effective_sample_size,
        "split_rhat": split_rhat,
    })
    acceptance_rates = posterior.attrs.get("acceptance_rates")
    diagnostics["mean_acceptance_rate"] = float(np.mean(acceptance_rates)) if acceptance_rates is not None else np.nan
    return diagnostics


def posterior_summary(posterior: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"parameter": posterior.columns, "posterior_mean": posterior.mean().to_numpy(), "median": posterior.median().to_numpy(), "credible_interval_2_5": posterior.quantile(0.025).to_numpy(), "credible_interval_97_5": posterior.quantile(0.975).to_numpy()})


def posterior_predictive(posterior: pd.DataFrame, observations: pd.DataFrame | None = None, samples: int = 150, seed: int = 9) -> pd.DataFrame:
    if observations is None:
        observations = load_observations()
    rng = np.random.default_rng(seed)
    chosen = posterior.iloc[rng.choice(len(posterior), size=min(samples, len(posterior)), replace=False)]
    simulations = []
    for _, row in chosen.iterrows():
        parameters = NPZDParameters(growth_rate=row.growth_rate_day, grazing_rate=row.grazing_rate_day, zooplankton_mortality=row.zooplankton_mortality_day)
        simulations.append(simulate_npzd(parameters, observations)["phytoplankton"].to_numpy() * row.chlorophyll_scale_mg_m3)
    values = np.asarray(simulations)
    return pd.DataFrame({"day": np.arange(values.shape[1]), "median_chlorophyll_mg_m3": np.median(values, axis=0), "lower_95": np.quantile(values, 0.025, axis=0), "upper_95": np.quantile(values, 0.975, axis=0)})
