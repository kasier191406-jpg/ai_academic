# Presentation outline

1. Motivation: Black Sea ecosystem monitoring and satellite observations.
2. Problem: biological parameters are uncertain.
3. Data: JRC MODIS-Aqua chlorophyll and NOAA OISST, bundled locally.
4. Processing: quality-screened spatial means with exact file provenance.
5. NPZD equations and SST/light forcing.
6. Bayesian observation model and Metropolis-Hastings sampler.
7. Dashboard results: posterior distributions and predictive uncertainty.
8. Limitations, ethics of data provenance, and future work.

# Viva questions and short answers

**What does NPZD mean?** Nutrient, phytoplankton, zooplankton, and detritus; they are simplified ecosystem compartments.

**Is chlorophyll the same as phytoplankton biomass?** No. It is a proxy. The model therefore estimates a chlorophyll scale parameter.

**Why use Bayesian estimation?** It returns a distribution of plausible parameter values and credible intervals, instead of only one best fit.

**What is the MCMC algorithm here?** Random-walk Metropolis-Hastings in log-parameter space.

**How do you know the sampler converged?** I do not claim convergence from the algorithm alone. I run independent chains and inspect autocorrelation-based effective sample sizes and split R-hat. These diagnostics can reveal poor mixing, but with only eleven observation dates they are not proof that the posterior is fully explored.

**What does a 95% credible interval mean?** Given the model, data, and prior, the posterior assigns 95% probability to values inside that interval.

**What priors and bounds are used?** Truncated log-normal priors on growth, grazing, zooplankton mortality, chlorophyll scale, and observation error, with the log means, standard deviations, and hard supports documented in the report.

**Why are intervals wide?** The bundled subset has only eleven dates, the chlorophyll data have cloud/quality-dependent coverage, parameters can trade off against each other, and the simplified model omits physical processes.

**Is the SST satellite-only?** No. OISST is a NOAA observation analysis that combines AVHRR satellite input with in-situ observations; the dashboard labels it accurately.

**Why is PAR missing?** A suitable public, credential-free Black Sea PAR subset was not bundled. The model uses a documented theoretical seasonal light factor instead.

**Does this reproduce the named research paper?** No. It is an academic prototype inspired by the general satellite-informed Bayesian ecosystem-modelling approach.

**How does the app work offline?** Raw and processed files, posterior samples, and all code are in the repository. The app reads them locally and has no runtime network dependency.

**Are the uncertainty bands complete predictive uncertainty?** No. They propagate parameter uncertainty only; they do not include satellite retrieval error, model structural error, or uncertainty from missing MLD/PAR observations.
