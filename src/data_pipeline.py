"""Create the small offline CSV from verified raw NetCDF observation files."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
CHL_DIR = ROOT / "data" / "raw" / "chlorophyll"
SST_DIR = ROOT / "data" / "raw" / "sst"
OUT_FILE = ROOT / "data" / "processed" / "black_sea_observations_2003.csv"


def _day_of_year(path: Path) -> int:
    match = re.search(r"2003(\d{3})", path.name)
    if not match:
        raise ValueError(f"No 2003 day-of-year in {path.name}")
    return int(match.group(1))


def _mean_chlorophyll(path: Path) -> tuple[float, int]:
    with xr.open_dataset(path) as dataset:
        variable = dataset["chlideachla"]
        values = variable.where((variable > 0) & (variable < 100)).values
        return float(np.nanmean(values)), int(np.isfinite(values).sum())


def _mean_sst(path: Path) -> float:
    with xr.open_dataset(path) as dataset:
        black_sea = dataset["sst"].sel(lat=slice(40.5, 48.0), lon=slice(27.0, 42.0))
        return float(black_sea.mean().item())


def build_processed_observations() -> pd.DataFrame:
    chlorophyll_files = sorted(CHL_DIR.glob("EMIS_D_chlideachla2003*_MODIS_EUR_BLCK.nc"))
    sst_files = sorted(SST_DIR.glob("sst_2003*.nc"))
    if len(chlorophyll_files) < 8 or len(sst_files) < 8:
        raise RuntimeError("At least eight verified chlorophyll and SST raw files are required.")
    chlorophyll = []
    for path in chlorophyll_files:
        mean, valid_pixels = _mean_chlorophyll(path)
        if valid_pixels:
            day = _day_of_year(path)
            chlorophyll.append((pd.Timestamp("2003-01-01") + pd.Timedelta(days=day - 1), mean, valid_pixels, path.name))
    sst = []
    for path in sst_files:
        with xr.open_dataset(path) as dataset:
            timestamp = pd.Timestamp(dataset["time"].values[0])
        sst.append((timestamp.normalize(), _mean_sst(path), path.name))
    chl_frame = pd.DataFrame(chlorophyll, columns=["date", "chlorophyll_mg_m3", "chlorophyll_valid_pixels", "chlorophyll_source_file"])
    sst_frame = pd.DataFrame(sst, columns=["date", "sst_c", "sst_source_file"])
    chl_frame["date"] = pd.to_datetime(chl_frame["date"]).astype("datetime64[ns]")
    sst_frame["date"] = pd.to_datetime(sst_frame["date"]).astype("datetime64[ns]")
    output = pd.merge_asof(chl_frame.sort_values("date"), sst_frame.sort_values("date"), on="date", direction="nearest", tolerance=pd.Timedelta(days=3))
    output = output.dropna().sort_values("date").reset_index(drop=True)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUT_FILE, index=False, float_format="%.6f")
    return output


if __name__ == "__main__":
    frame = build_processed_observations()
    print(f"Wrote {len(frame)} processed observation rows to {OUT_FILE}")
