# OceanSense AI: Satellite-Based Marine Ecosystem Monitoring and Bayesian Parameter Estimation

## Abstract

OceanSense AI is an offline academic prototype for exploring Black Sea phytoplankton variability. It bundles real MODIS-Aqua chlorophyll-a maps and NOAA OISST observations, derives transparent spatial summaries, simulates a reduced nutrient-phytoplankton-zooplankton-detritus (NPZD) ecosystem, and calibrates selected parameters with Metropolis-Hastings Bayesian inference. The project is inspired by work on satellite-informed Black Sea ecosystem estimation but is not a reproduction of a full process-based or particle-MCMC study.

## Introduction and problem statement

Phytoplankton responds to light, nutrients, temperature, grazing, and physical mixing. Satellite chlorophyll provides broad spatial coverage but is an indirect surface measurement, while ecosystem models contain uncertain biological parameters. The problem addressed here is how a small, reproducible application can combine observed chlorophyll and SST with a numerical ecosystem model and make parameter uncertainty visible.

## Objectives

1. Bundle inspectable real Black Sea chlorophyll-a and SST observations.
2. Provide offline visual exploration of the observations.
3. Simulate an NPZD model with real SST temperature forcing.
4. Estimate selected model parameters with a genuine Bayesian MCMC method.
5. Show posterior distributions, 95% credible intervals, and posterior predictive uncertainty.

## Research-paper connection and literature background

The project follows the general idea that satellite chlorophyll can reduce uncertainty in marine ecosystem models. It is academically inspired by the stated Black Sea Bayesian-estimation paper topic. It does not claim the same domain model, forcing fields, prior specification, assimilation system, or PMCMC implementation. Core background sources are Grégoire, Vandenbulcke, and Capet (2020) for Black Sea biogeochemical reanalysis context; Reynolds et al. (2007) for daily OISST; and the JRC EMIS product documentation for satellite chlorophyll.

## System architecture

```text
Bundled NetCDF files -> data_pipeline.py -> processed CSV -> Streamlit dashboard
                                                    -> NPZD RK4 model -> MCMC posterior -> predictive bands
```

The dashboard reads `data/processed/` locally. It does not request an API token or internet connection after the repository and packages are installed.

## Dataset description

The JRC EMIS MODIS-Aqua daily chlorophyll maps are real satellite-derived observations in mg m⁻³. The project selects eleven 2003 dates and computes a valid-pixel spatial mean. NOAA OISST v2.1 provides real observation-based Level-4 SST in °C; the project averages the Black Sea region 40.5–48°N, 27–42°E on matching dates. Exact file names, date coverage, units, coordinates, and processing are recorded in `data/DATASET_METADATA.md`.

The requested Copernicus OMI monthly series requires registration, so it is not represented as downloaded. MLD and PAR are unavailable in the bundled observation subset. No synthetic SST, MLD, PAR, or chlorophyll is presented as a measurement.

## NPZD mathematical methodology

The model state is `X = [N, P, Z, D]`, where N is nutrient, P is phytoplankton, Z is zooplankton, and D is detritus. For production `G`, grazing `H`, phytoplankton loss `mP`, zooplankton loss `mZ`, and remineralization `rD`:

```text
G = mu * exp(0.063 * (SST - 15)) * L(t) * N/(K_N + N) * P
H = g * P/(0.30 + P) * Z
dN/dt = -G + rD
dP/dt =  G - H - mP*P
dZ/dt =  aH - mZ*Z²
dD/dt =  mP*P + (1-a)H + mZ*Z² - rD - sD
```

`L(t)` is a dimensionless seasonal light assumption constrained to 0.12–1.0. It is a model input, not a PAR observation. Real bundled SST is interpolated to the daily model grid; outside the first and last observed dates, the nearest endpoint temperature is held constant. The solver uses fourth-order Runge-Kutta with a one-day step and protects state concentrations from becoming negative. With the equations above, internal transfers cancel in `d(N+P+Z+D)/dt`; only the detritus-sinking term removes modeled mass.

The fixed values are `K_N = 0.45`, grazing half-saturation `0.30`, assimilation efficiency `a = 0.65`, phytoplankton mortality `mP = 0.045 day⁻¹`, remineralization `r = 0.08 day⁻¹`, sinking `s = 0.025 day⁻¹`, and initial state `[N,P,Z,D] = [1.2,0.25,0.12,0.20]`. These are simplified model assumptions, not estimated from the eleven satellite dates; state concentrations are relative model units.

## Bayesian estimation methodology

The observation model is `log(Chl_obs) ~ Normal(log(scale * P_model), sigma)`. Unknown positive parameters are phytoplankton growth `mu`, grazing `g`, zooplankton mortality `mZ`, chlorophyll scale, and log-observation error `sigma`.

| Parameter | Log-prior mean (natural-scale reference) | Log-prior SD | Hard support |
|---|---:|---:|---:|
| Growth `mu` (day⁻¹) | `ln(0.75)` | 0.55 | (0.01, 4) |
| Grazing `g` (day⁻¹) | `ln(0.38)` | 0.55 | (0.005, 3) |
| Zooplankton mortality `mZ` (day⁻¹) | `ln(0.11)` | 0.60 | (0.002, 2) |
| Chlorophyll scale (mg m⁻³ per relative P) | `ln(5)` | 1.00 | (0.05, 100) |
| Observation log-SD `sigma` | `ln(0.45)` | 0.50 | (0.03, 3) |

These are truncated log-normal priors (normal priors on log parameters with the stated hard bounds). The sampler proposes a symmetric Gaussian random walk in log space with proposal SDs `[0.45, 0.45, 0.45, 0.375, 0.30]`. Independent chains use different seeded starting points; the saved run and dashboard button retain draws after each chain's burn-in. `posterior_diagnostics.csv` reports autocorrelation-based effective sample size (ESS), split R-hat, and mean acceptance rate. ESS and R-hat are diagnostics, not proof of convergence.

## Implementation details

Python packages are Streamlit, Pandas, NumPy, SciPy, Plotly, Matplotlib, xarray, and h5netcdf. `src/data_pipeline.py` produces the processed CSV from bundled NetCDF. `src/model.py` contains all equations, inference, and diagnostics. `app.py` contains the offline dashboard.

## Results and discussion

The bundled result was generated with four independent Metropolis-Hastings chains, 2,000 iterations each and 500 burn-in iterations per chain (6,000 retained samples total). Per-chain acceptance rates were 0.188–0.210 (mean 0.199). Split R-hat was 1.02–1.04 and estimated ESS was 87–258 across parameters. These diagnostics show some agreement between chains, but the modest ESS means Monte Carlo error remains; they do not establish convergence.

| Parameter | Posterior median | Equal-tail 95% credible interval |
|---|---:|---:|
| Growth `mu` (day⁻¹) | 1.614 | 0.499–3.488 |
| Grazing `g` (day⁻¹) | 0.141 | 0.056–0.321 |
| Zooplankton mortality `mZ` (day⁻¹) | 0.174 | 0.064–0.605 |
| Chlorophyll scale | 6.954 | 2.744–21.867 |
| Observation log-SD `sigma` | 1.063 | 0.725–1.599 |

These are posterior summaries conditional on the specified priors, hard bounds, and simplified model, not independent ecological measurements. The broad intervals and limited ESS are expected with only eleven cloud-screened dates, five estimated parameters, and parameter trade-offs.

## Limitations and future scope

The selected data cover eleven dates in 2003 rather than the full Copernicus 1997–2024 monthly record. The spatial means hide regional gradients. OISST is a blended observation analysis rather than a Black Sea Copernicus L3S subset. There are no bundled MLD or PAR observations. Future work should obtain registered Copernicus subsets, add MLD/PAR forcing, use spatial observations, increase effective posterior sample sizes, and test a richer NPZD model.

## Conclusion

OceanSense AI provides a working local demonstration of transparent observation processing, NPZD simulation, Bayesian posterior sampling, credible intervals, and model-observation comparison. It supports a classroom discussion of what observations constrain, what remains uncertain, and why provenance matters.

## References

1. Melin, F. (2016). EMIS - BLACK SEA Daily sea surface Chlorophyll-a concentration in mg.m⁻3. European Commission JRC. PID: `http://data.europa.eu/89h/2daecf2a-9fcc-4fa3-9c8b-d91513673163`.
2. Huang, B. et al. (2021). Improvements of the Daily Optimum Interpolation Sea Surface Temperature (DOISST) Version 2.1. Journal of Climate. NOAA dataset DOI: `10.25921/RE9P-PT57`.
3. Grégoire, M., Vandenbulcke, L., & Capet, A. (2020). Black Sea Biogeochemical Reanalysis. Copernicus Marine Service. DOI: `10.25423/CMCC/BLKSEA_REANALYSIS_BIO_007_005`.
4. Copernicus Marine Service. OMI Black Sea chlorophyll-a time series and trend from observations reprocessing. DOI: `10.48670/moi-00211`.
