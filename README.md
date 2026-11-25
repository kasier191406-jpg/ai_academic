# MARIS

MARIS is a local marine-science analysis application with a React/Vite JavaScript frontend and a FastAPI backend. The backend reuses the existing Python NPZD, Metropolis–Hastings, upload-validation, and date-specific prediction implementations. Source observations and posterior artifacts are bundled; runtime analysis does not fetch data or call external APIs.

## Requirements

- Python 3.10 or later
- Node.js 20 or later and npm
- Windows users can use the provided `run.bat`

## Install once

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

## Run

On Windows, run `run.bat` from the project directory. It opens separate local API and frontend terminals. Visit:

- Web application: <http://127.0.0.1:5173>
- FastAPI documentation: <http://127.0.0.1:8000/docs>

Alternatively, start each service in its own terminal:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

The Vite development server proxies `/api` requests to the local FastAPI service. Stop each process by closing its terminal or pressing Ctrl+C there. Dependency installation may need network access once; the running application uses only local files and localhost services.

## Application pages

The navigation includes Overview, Dataset Explorer, Ocean Observation Analysis, Sea Surface Temperature, Chlorophyll-a, NPZD Ecosystem Model, Bayesian Parameter Estimation, Dataset Upload, Interactive Prediction, Prediction and Uncertainty, and Results and Limitations.

Dataset Upload accepts CSV files with `date`, `sst_c`, and `chlorophyll_mg_m3` columns. The API validates the data and holds it in memory for the current backend process; it never replaces bundled observations. Interactive Prediction uses the existing model prediction workflow and requires at least two SST observations in the selected calendar year. Uploaded chlorophyll is displayed only as a comparison and is not used to fit the bundled posterior. Predictions for selected observation dates are not future forecasts.

The Bayesian page initially displays the bundled posterior artifacts. Fresh four-chain Metropolis–Hastings estimation is run only when explicitly requested and may take a few minutes on a laptop.

## Data and scientific scope

`data/processed/black_sea_observations_2003.csv` contains eleven paired dates from 2003. Chlorophyll-a is sourced from the JRC EMIS Black Sea MODIS-Aqua product; SST is from NOAA OISST v2.1, a Level-4 analysis using satellite and in-situ inputs. Raw NetCDF inputs and provenance are retained under `data/`. September is absent and is not fabricated. See [dataset metadata](data/DATASET_METADATA.md).

The model is a simplified NPZD implementation driven by observed SST and an explicit dimensionless seasonal-light assumption. MLD and PAR are not bundled observations. The Bayesian method is random-walk Metropolis–Hastings, not a reproduction of the referenced paper's PMCMC workflow. Posterior intervals are conditional on this model and propagate parameter uncertainty only; they exclude observation/retrieval and structural-model uncertainty. The small number of observation dates limits parameter identification and convergence assessment.

## Backend API

- `GET /api/health`, `/api/metadata`, `/api/observations`
- `GET /api/model-info`, `/api/npzd`, `/api/posterior`, `/api/prediction-uncertainty`
- `POST /api/bayesian/estimate` to explicitly run fresh chains
- `POST /api/uploads`, `GET`/`DELETE /api/uploads/{upload_id}`
- `POST /api/predictions`

The existing scientific modules live in `backend/src/`. Small compatibility modules under `src/` preserve the prior Python import paths used by project scripts and tests.

## Verify

```powershell
python -m compileall -q backend src tests
pytest -q
python -m pip check
cd frontend
npm run build
```

Tests cover the bundled raw/processed data, NPZD numerical properties, MCMC summaries and diagnostics, CSV validation, API response schemas, and prediction endpoints.

The original academic documentation remains under `documentation/`; it describes the scientific project and is not required to run the application.
