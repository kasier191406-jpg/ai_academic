# Professor demonstration guide (5–7 minutes)

## Before the demonstration

Install dependencies once if needed; this is the only step that may require internet access:

```bat
py -m pip install -r requirements.txt
```

In the project directory, start the already-installed app with:

```bat
py -m streamlit run app.py --browser.gatherUsageStats false
```

Alternatively, double-click `run.bat`. It disables Streamlit usage statistics and does not install packages. Once started, the application and full demonstration use only bundled project files; no API, credentials, or downloads are required.

## Walkthrough

1. **Overview (30 seconds):** Show the count and ranges of the 11 observed dates. Explain that chlorophyll is from JRC MODIS-Aqua and SST from NOAA OISST, and that the NOAA analysis combines satellite and in-situ inputs.
2. **Dataset Explorer (45 seconds):** Show the actual date rows, units, valid-pixel counts, and both source-filename columns. Point out that September is missing rather than filled in.
3. **Observation plots (60 seconds):** Open **SST Analysis** and **Chlorophyll-a Analysis**. Identify the measured quantities and units; explain that chlorophyll's valid spatial coverage varies with cloud/quality screening.
4. **NPZD model (60 seconds):** Open **NPZD Ecosystem Model**. Explain nutrient, phytoplankton, zooplankton, and detritus; real SST forces temperature response, while seasonal light is an assumption because no PAR measurement is bundled.
5. **Bayesian results (90 seconds):** Open **Bayesian Parameter Estimation**. Show posterior means/medians, equal-tail 95% credible intervals, parameter histogram, ESS and split R-hat. Explain that intervals are conditional on this simplified model, priors, and eleven dates; diagnostics are not proof of convergence.
6. **Prediction (45 seconds):** Open **Prediction and Uncertainty Analysis**. Identify satellite observations, posterior median, and parameter-only 95% interval; it does not include retrieval or structural model error.
7. **Limitations (45 seconds):** Finish on **Results and Model Limitations**. State explicitly: only 11 dates in 2003, no observed MLD/PAR, small and cloud-dependent chlorophyll coverage, and a reduced model that is not the paper's PMCMC implementation.

The precomputed posterior makes the walkthrough immediate and offline. If time permits, click **Run fresh Bayesian estimation** on the Bayesian page to run four new local Metropolis-Hastings chains; this additional computation may take a few minutes on a laptop.
