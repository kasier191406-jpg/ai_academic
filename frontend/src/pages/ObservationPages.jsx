import { useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { ArrowDownToLine, Search } from "lucide-react";
import { csvUrl } from "../api";
import { ChartTooltip, dateLabel, Metric, PageHeader, Panel, State, useResource } from "../components";

const axis = { axisLine: false, tickLine: false, tick: { fill: "#82949c", fontSize: 9 } };
const grid = <CartesianGrid stroke="#e9eff1" vertical={false} />;
const dateTick = (value) => new Date(`${value}T00:00:00`).toLocaleDateString("en", { month: "short", day: "numeric" });

function ObservationChart({ rows, field, color, label, unit, domain, height = "tall" }) {
  return (
    <div className={`chart-wrap ${height}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          {grid}
          <XAxis dataKey="date" tickFormatter={dateTick} minTickGap={22} {...axis} />
          <YAxis domain={domain || ["auto", "auto"]} width={44} tickFormatter={(v) => Number(v).toFixed(field === "sst_c" ? 0 : 1)} {...axis} />
          <Tooltip content={<ChartTooltip formatter={(value) => `${Number(value).toFixed(field === "sst_c" ? 2 : 3)} ${unit}`} />} />
          <Line type="monotone" dataKey={field} name={label} stroke={color} strokeWidth={2.2}
            dot={{ r: 3.4, strokeWidth: 1.5, fill: "#fff" }} activeDot={{ r: 5, strokeWidth: 0 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function OverviewPage() {
  const { data: metadata, loading: metadataLoading, error: metadataError } = useResource("/metadata");
  const { data: observationData, loading, error } = useResource("/observations");
  const rows = observationData?.rows || [];
  return (
    <>
      <div className="hero">
        <div>
          <div className="eyebrow">Black Sea · observation system</div>
          <h1>MARIS</h1>
          <p>Explore satellite-derived chlorophyll-a and sea-surface temperature with a transparent ecosystem model and Bayesian parameter analysis.</p>
        </div>
        {metadata && <div className="hero-aside"><span>Observation window</span><strong>{dateLabel(metadata.start_date)} – {dateLabel(metadata.end_date)}</strong><small>Paired regional means · {metadata.observation_count} dates</small></div>}
      </div>
      <State loading={metadataLoading || loading} error={metadataError || error}>
        {metadata && (
          <>
            <div className="grid grid-3">
              <Metric label="Paired observation dates" value={metadata.observation_count} note="Selected 2003 dates · September absent" />
              <Metric label="Chlorophyll-a range" value={`${metadata.chlorophyll_range_mg_m3[0].toFixed(2)}–${metadata.chlorophyll_range_mg_m3[1].toFixed(2)}`} note="mg/m³ · JRC EMIS MODIS-Aqua" accent="blue" />
              <Metric label="Sea-surface temperature" value={`${metadata.sst_range_c[0].toFixed(1)}–${metadata.sst_range_c[1].toFixed(1)} °C`} note="NOAA OISST v2.1 Level-4 analysis" accent="gold" />
            </div>
            <div className="grid grid-2 section-spacer">
              <Panel title="Observed sea-surface temperature" subtitle="Regional mean · NOAA OISST v2.1 · °C">
                <ObservationChart rows={rows} field="sst_c" color="#397496" label="SST" unit="°C" height="compact" />
              </Panel>
              <Panel title="Observed chlorophyll-a" subtitle="Spatial mean of valid pixels · mg/m³">
                <ObservationChart rows={rows} field="chlorophyll_mg_m3" color="#287f80" label="Chlorophyll-a" unit="mg/m³" height="compact" />
              </Panel>
            </div>
            <div className="layout-main-aside section-spacer">
              <Panel title="Project workflow" subtitle="A local, reproducible path from observations to model-based interpretation">
                <div className="grid grid-3">
                  <div className="workflow-tile"><span>01</span><strong>Observe</strong><p>Inspect measured regional means, source files, and valid-pixel coverage.</p></div>
                  <div className="workflow-tile"><span>02</span><strong>Model</strong><p>Run the NPZD equations using observed SST and documented light forcing.</p></div>
                  <div className="workflow-tile"><span>03</span><strong>Quantify</strong><p>Review posterior parameters and uncertainty for selected observation dates.</p></div>
                </div>
              </Panel>
              <Panel title="Data provenance">
                <div className="source-item"><span className="source-symbol blue">SST</span><div><strong>Sea-surface temperature</strong><p>{metadata.sst_source}</p></div></div>
                <div className="source-item"><span className="source-symbol teal">CHL</span><div><strong>Chlorophyll-a</strong><p>{metadata.chlorophyll_source}</p></div></div>
                <div className="callout warn">MLD and PAR are not bundled observations. Seasonal light is a model assumption; predictions are not future forecasts.</div>
              </Panel>
            </div>
          </>
        )}
      </State>
    </>
  );
}

export function DatasetExplorerPage() {
  const { data, loading, error } = useResource("/observations");
  const [query, setQuery] = useState("");
  const rows = data?.rows || [];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle ? rows.filter((row) => Object.values(row).some((value) => String(value).toLowerCase().includes(needle))) : rows;
  }, [rows, query]);
  const download = () => {
    const url = csvUrl(rows, Object.keys(rows[0] || {}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "black_sea_observations_2003.csv";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  return (
    <>
      <PageHeader eyebrow="Data analysis" title="Dataset Explorer" description="Browse the bundled processed observations with their units, coverage and raw NetCDF provenance." />
      <State loading={loading} error={error}>
        <Panel title="Processed Black Sea observations" subtitle={`${filtered.length} of ${rows.length} observed records`} action={<button className="button-secondary" onClick={download}><ArrowDownToLine size={14} /> Export CSV</button>}>
          <div className="table-tools">
            <label className="search-control"><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search dates, values or source files" aria-label="Search observations" /></label>
            <span className="status-pill">Bundled · read only</span>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Date</th><th className="numeric">Chlorophyll-a (mg/m³)</th><th className="numeric">Valid pixels</th><th>SST (°C)</th><th>Chlorophyll source file</th><th>SST source file</th></tr></thead>
              <tbody>{filtered.map((row) => <tr key={row.date}>
                <td>{row.date}</td><td className="numeric">{Number(row.chlorophyll_mg_m3).toFixed(3)}</td><td className="numeric">{Number(row.chlorophyll_valid_pixels).toLocaleString()}</td>
                <td>{Number(row.sst_c).toFixed(2)}</td><td title={row.chlorophyll_source_file}>{row.chlorophyll_source_file}</td><td>{row.sst_source_file}</td>
              </tr>)}</tbody>
            </table>
            {!filtered.length && <div className="empty-state">No observations match this search.</div>}
          </div>
          <p className="muted-note">Each row is a spatial mean for one observed date. The source-file columns link each value to its bundled raw NetCDF input; missing September observations are not filled.</p>
        </Panel>
      </State>
    </>
  );
}

function ScatterTooltip({ active, payload }) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return <div className="chart-tooltip"><div className="tooltip-date">{dateLabel(row.date)}</div><div className="tooltip-line"><i style={{ background: "#397496" }} /><span>SST</span><strong>{Number(row.sst_c).toFixed(2)} °C</strong></div><div className="tooltip-line"><i style={{ background: "#287f80" }} /><span>Chlorophyll-a</span><strong>{Number(row.chlorophyll_mg_m3).toFixed(3)} mg/m³</strong></div><div className="tooltip-line"><span>Valid pixels</span><strong>{Number(row.chlorophyll_valid_pixels).toLocaleString()}</strong></div></div>;
}

export function ObservationPage() {
  const { data, loading, error } = useResource("/observations");
  const { data: metadata, loading: metadataLoading, error: metadataError } = useResource("/metadata");
  const rows = data?.rows || [];
  return (
    <>
      <PageHeader eyebrow="Data analysis" title="Ocean Observation Analysis" description="Compare paired satellite chlorophyll-a and NOAA sea-surface temperature observations without implying causality." />
      <State loading={loading || metadataLoading} error={error || metadataError}>
        {metadata && rows.length > 0 && <>
          <div className="grid grid-3">
            <Metric label="Paired observations" value={rows.length} note={`${dateLabel(rows[0].date)} to ${dateLabel(rows[rows.length - 1].date)}`} />
            <Metric label="Mean SST" value={`${metadata.sst_mean_c.toFixed(2)} °C`} note="NOAA OISST regional mean" accent="blue" />
            <Metric label="Mean valid chl pixels" value={Math.round(metadata.mean_chlorophyll_valid_pixels).toLocaleString()} note={`Mean chlorophyll ${metadata.chlorophyll_mean_mg_m3.toFixed(3)} mg/m³`} accent="gold" />
          </div>
          <Panel className="section-spacer" title="Joint observation space" subtitle="Each point is a paired date · colour indicates cloud-screened valid chlorophyll pixels">
            <div className="chart-wrap tall"><ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 18, bottom: 12, left: 5 }}>
                {grid}
                <XAxis type="number" dataKey="sst_c" name="SST" unit=" °C" domain={["dataMin - 2", "dataMax + 2"]} label={{ value: "Sea-surface temperature (°C)", position: "insideBottom", offset: -3, fill: "#758992", fontSize: 10 }} {...axis} />
                <YAxis type="number" dataKey="chlorophyll_mg_m3" name="Chlorophyll-a" unit=" mg/m³" width={55} label={{ value: "Chlorophyll-a (mg/m³)", angle: -90, position: "insideLeft", fill: "#758992", fontSize: 10 }} {...axis} />
                <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: "3 3" }} />
                <Scatter data={rows} fill="#287f80">
                  {rows.map((row) => <Cell key={row.date} fill={Number(row.chlorophyll_valid_pixels) < 5000 ? "#a98756" : "#287f80"} />)}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer></div>
            <div className="chart-legend"><span className="legend-item"><i style={{ background: "#287f80" }} /> Higher valid-pixel coverage</span><span className="legend-item"><i style={{ background: "#a98756" }} /> Lower valid-pixel coverage</span></div>
          </Panel>
          <div className="callout">These are observed product values paired by date. This descriptive comparison does not imply a causal relationship; spatial sampling of chlorophyll varies with cloud and quality screening.</div>
        </>}
      </State>
    </>
  );
}

export function SSTPage() {
  const { data, loading, error } = useResource("/observations");
  const { data: metadata, loading: metadataLoading, error: metadataError } = useResource("/metadata");
  const rows = data?.rows || [];
  return (
    <>
      <PageHeader eyebrow="Ocean observations" title="Sea Surface Temperature" description="Regional sea-surface temperature from NOAA OISST v2.1, shown in degrees Celsius at the selected observation dates." />
      <State loading={loading || metadataLoading} error={error || metadataError}>
        {metadata && rows.length > 0 && <>
        <div className="grid grid-3">
          <Metric label="Mean observed SST" value={`${metadata.sst_mean_c.toFixed(2)} °C`} note="Across bundled paired dates" accent="blue" />
          <Metric label="Minimum" value={`${metadata.sst_range_c[0].toFixed(2)} °C`} note={dateLabel(metadata.sst_min_date)} />
          <Metric label="Maximum" value={`${metadata.sst_range_c[1].toFixed(2)} °C`} note={dateLabel(metadata.sst_max_date)} accent="gold" />
        </div>
        <Panel className="section-spacer" title="Observed monthly spatial-mean temperature" subtitle="Measured regional SST · connecting segments are visual guides between sampling dates">
          <ObservationChart rows={rows} field="sst_c" color="#397496" label="SST" unit="°C" />
        </Panel>
        <div className="callout">NOAA OISST is a Level-4 analysis using satellite and in-situ inputs, not a pure satellite-only series. September 2003 is absent from the bundled subset.</div>
        </>}
      </State>
    </>
  );
}

export function ChlorophyllPage() {
  const { data, loading, error } = useResource("/observations");
  const { data: metadata, loading: metadataLoading, error: metadataError } = useResource("/metadata");
  const rows = data?.rows || [];
  return (
    <>
      <PageHeader eyebrow="Ocean observations" title="Chlorophyll-a Analysis" description="Spatial-mean chlorophyll-a from the JRC EMIS Black Sea MODIS-Aqua product, with pixel coverage shown alongside concentration." />
      <State loading={loading || metadataLoading} error={error || metadataError}>
        {metadata && rows.length > 0 && <>
        <div className="grid grid-2">
          <Metric label="Mean chlorophyll-a" value={`${metadata.chlorophyll_mean_mg_m3.toFixed(3)} mg/m³`} note="Valid positive pixels only" />
          <Metric label="Valid-pixel range" value={`${metadata.chlorophyll_valid_pixels_range[0].toLocaleString()}–${metadata.chlorophyll_valid_pixels_range[1].toLocaleString()}`} note="Coverage varies with cloud and quality screening" accent="blue" />
        </div>
        <Panel className="section-spacer" title="Observed chlorophyll-a concentration" subtitle="JRC EMIS Black Sea MODIS-Aqua · mg/m³">
          <ObservationChart rows={rows} field="chlorophyll_mg_m3" color="#287f80" label="Chlorophyll-a" unit="mg/m³" domain={[0, "auto"]} />
        </Panel>
        <Panel className="section-spacer" title="Valid satellite pixels contributing to each mean" subtitle="Counts indicate spatial coverage after cloud and quality screening">
          <div className="chart-wrap compact"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 6, right: 10, bottom: 0, left: 2 }}>
              {grid}<XAxis dataKey="date" tickFormatter={dateTick} minTickGap={22} {...axis} />
              <YAxis width={48} tickFormatter={(value) => `${Math.round(value / 1000)}k`} {...axis} />
              <Tooltip content={<ChartTooltip formatter={(value) => `${Number(value).toLocaleString()} pixels`} />} />
              <Bar dataKey="chlorophyll_valid_pixels" name="Valid pixels" fill="#597f94" maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer></div>
        </Panel>
        <div className="callout">A low valid-pixel count means less spatial coverage after cloud/quality screening; it does not necessarily mean lower chlorophyll concentration.</div>
        </>}
      </State>
    </>
  );
}
