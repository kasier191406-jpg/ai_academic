# OceanSense AI

OceanSense AI is an offline Streamlit demonstration of Black Sea ecosystem monitoring. It combines bundled real chlorophyll-a and SST observations with a simplified NPZD model and a Metropolis-Hastings Bayesian calibration.

## Run on Windows

Install packages once (this setup step may need internet access):

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then launch with:

```bat
.venv\Scripts\python.exe -m streamlit run app.py --browser.gatherUsageStats false
```

Or double-click `run.bat`; it uses the local `.venv` if present, otherwise the Python launcher environment. It does not install packages, send Streamlit usage statistics, or download data. Bundled files under `data/` are read-only; optional CSV uploads remain in Streamlit session memory and do not modify those files.

## Upload and interactive prediction

Open **Dataset Upload** to download a CSV template or upload a file with `date`, `sst_c`, and `chlorophyll_mg_m3` columns. The dashboard validates and previews uploaded rows and keeps them separate from the bundled dataset for the current session.

In **Interactive Prediction**, choose a dataset and an observation date, then run the prediction. The date-specific posterior predictive estimate reuses the bundled Bayesian posterior and NPZD model; uploaded chlorophyll is only shown as the observed comparison, while uploaded SST is used as model forcing. Prediction requires at least two SST observations in the selected calendar year. This is an estimate for an observed date, not a future forecast. Its 95% interval propagates parameter uncertainty only and excludes retrieval and structural model uncertainty.

## Bundled observations

`data/processed/black_sea_observations_2003.csv` contains eleven real 2003 observation dates. Chlorophyll-a comes from the European Commission JRC EMIS Black Sea MODIS-Aqua product (`chlideachla`, mg/m³). SST comes from NOAA OISST v2.1 (`sst`, °C). `data/raw/` retains the exact NetCDF source files used by the processing script, and each CSV row records its source filenames.

The requested Copernicus monthly OMI product requires registered access. The project therefore does not claim that its JRC source is the Copernicus monthly record. See `data/DATASET_METADATA.md` for coverage, processing, attribution, and limitations.

## Scientific scope

The NPZD model has nutrient, phytoplankton, zooplankton, and detritus states. A log-normal observational model relates simulated phytoplankton to satellite chlorophyll. Random-walk Metropolis-Hastings samples posterior distributions for growth, grazing, zooplankton mortality, chlorophyll scale, and observation error. This is a simplified academic implementation inspired by Black Sea Bayesian ecosystem modelling, not a reproduction of a published PMCMC workflow.

## Verification

```bat
python -m compileall -q app.py src tests
pytest -q
```

The tests exercise the offline data pipeline, raw observation metadata, NPZD mass balance, multi-chain posterior diagnostics, CSV upload validation, and date-specific predictions. Rebuilding the processed CSV from bundled NetCDF files is optional:

```bat
python -m src.data_pipeline
```

See [the academic report](documentation/ACADEMIC_REPORT.md), [professor demonstration guide](documentation/DEMONSTRATION_GUIDE.md), [viva questions](documentation/VIVA_AND_PRESENTATION.md), and [dataset provenance](data/DATASET_METADATA.md).
