# Dataset metadata and attribution

## Processed offline file

`processed/black_sea_observations_2003.csv` has 11 selected 2003 dates: 15 January, 15 February, 15 March, 15 April, 15 May, 15 June, 15 July, 15 August, 15 October, 15 November, and 15 December. September was absent from the selected source-file sequence and is not interpolated or fabricated.

| Field | Meaning | Units | Processing |
|---|---|---|---|
| `chlorophyll_mg_m3` | Spatial mean chlorophyll-a | mg m⁻³ | Mean of finite, valid positive JRC grid cells below 100 mg m⁻³ |
| `chlorophyll_valid_pixels` | Valid cells in the source map | count | Cloud/quality masking affects this count |
| `sst_c` | Spatial mean sea-surface temperature | °C | Mean of NOAA OISST cells over 40.5–48°N, 27–42°E |

Every processed row names its chlorophyll and SST source file. The monthly sampling dates are exact matches; the pipeline's three-day merge tolerance does not interpolate observations. The chlorophyll mean is computed over the valid pixels actually present, so the spatial sampling footprint changes with cloud/quality coverage. Processed data are a compact teaching subset, not a complete monthly climatology.

## Chlorophyll-a source

European Commission, Joint Research Centre (JRC), **EMIS - BLACK SEA Daily sea surface Chlorophyll-a concentration in mg.m⁻3**, PID `http://data.europa.eu/89h/2daecf2a-9fcc-4fa3-9c8b-d91513673163`, accessed 19 November 2026. The raw maps were downloaded from the JRC public directory and are bundled in `raw/chlorophyll/`. The product uses MODIS-Aqua satellite observations and a regional Black Sea bio-optical algorithm. Its grid spans 40.75–47.48°N and 27.28–42.00°E at approximately 2 km. The JRC catalogue states no access limitations and the European Commission reuse notice.

The NetCDF variable is `chlideachla` (units attribute `mg/m-3`) on 375 latitude by 588 longitude coordinates. Twelve files are retained: eleven maps used by the processed CSV and `chl_20030115.nc`, a byte-identical copy of the 15 January map. The processing script selects the `EMIS_D_...` source names; both copies remain bundled for provenance and are not double-counted.

## SST source

NOAA National Centers for Environmental Information, **NOAA 1/4° Daily Optimum Interpolation Sea Surface Temperature (OISST), Version 2.1**, DOI `10.25921/RE9P-PT57`, accessed 19 November 2026. Raw NetCDF files are bundled in `raw/sst/`. OISST is a Level-4 observation analysis using AVHRR satellite input with ship, buoy, and other in-situ observations; it is not labelled as a pure satellite-only series. The bundled variable is `sst`, Celsius.

The twelve SST files each contain one daily timestamp at 12:00 UTC, with global 0.25° latitude/longitude coordinates; the source variable uses `Celsius`. The CSV contains a regional spatial mean for the Black Sea bounding box above, not a single grid cell or a basin-wide Copernicus product.

## Copernicus context and variables not bundled

The requested Copernicus OMI Black Sea chlorophyll product (`omi_health_chl_blksea_oceancolour_area_averaged_mean`, DOI `10.48670/moi-00211`) advertises monthly values from June 1997 to December 2024 but requires registered download access. It was inspected but could not be retrieved without credentials in this environment. MLD and PAR were also not bundled because no compatible credential-free Black Sea product was successfully obtained. The application does not show either as an observation. A dimensionless seasonal light term appears only as an explicit NPZD modelling assumption.
