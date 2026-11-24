import { useMemo, useState } from "react";
import {
  Area, Bar, CartesianGrid, Cell, ComposedChart, Line, LineChart,
  ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { LoaderCircle, Play } from "lucide-react";
import { api } from "../api";
import {
  ChartTooltip, Metric, PageHeader, Panel, parameterLabels, parameterUnits, State, useResource,
} from "../components";

const axis = { axisLine: false, tickLine: false, tick: { fill: "#82949c", fontSize: 9 } };
const grid = <CartesianGrid stroke="#e9eff1" vertical={false} />;
const stateColors = { nutrient: "#24475b", phytoplankton: "#27847e", zooplankton: "#ba894d", detritus: "#6689a0" };
export function NPZDPage() {
  const [days, setDays] = useState(365);
  const { data: model, loading: modelLoading, error: modelError } = useResource("/model-info");
  const { data, loading, error } = useResource(`/npzd?days=${days}`);
  const states = model?.states || [];
  return (
    <>
      <PageHeader eyebrow="Ecosystem modelling" title="NPZD Ecosystem Model" description="Daily numerical integration of nutrient, phytoplankton, zooplankton and detritus states using the bundled SST forcing." />
      <State loading={modelLoading || loading} error={modelError || error}>
        {data && <>
          <div className="panel model-controls">
            <div><strong>Simulation horizon</strong><span>Default model parameters · deterministic run</span></div>
            <select className="select-control" aria-label="Simulation horizon" value={days} onChange={(event) => setDays(Number(event.target.value))}>
              <option value={180}>180 days</option><option value={365}>365 days</option>
            </select>
          </div>
          <div className="grid grid-2 section-spacer">
            {states.map(({ key, label, unit }) => (
              <Panel key={key} title={label} subtitle={`Simulated state · ${unit}`}>
                <div className="chart-wrap compact"><ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.rows} margin={{ top: 8, right: 12, bottom: 1, left: 0 }}>
                    {grid}<XAxis dataKey="day" tickFormatter={(value) => `d${value}`} minTickGap={30} {...axis} />
                    <YAxis width={43} {...axis} /><Tooltip content={<ChartTooltip formatter={(value) => `${Number(value).toFixed(3)} relative units`} />} />
                    <Line type="monotone" dataKey={key} name={label} stroke={stateColors[key]} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer></div>
              </Panel>
            ))}
          </div>
          <div className="callout">All curves are simulated model states, not measured concentrations. SST is observed temperature forcing; seasonal light is a dimensionless model assumption because PAR is not available as a bundled observation.</div>
        </>}
      </State>
    </>
  );
}

function ParameterHistogram({ distribution }) {
  const bins = distribution?.bins || [];
  const low = distribution?.credible_interval_2_5;
  const high = distribution?.credible_interval_97_5;
  const median = distribution?.median;
  return (
    <div className="chart-wrap tall"><ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={bins} margin={{ top: 12, right: 15, bottom: 14, left: 5 }}>
        {grid}<XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]} tickFormatter={(value) => Number(value).toPrecision(2)} {...axis} />
        <YAxis width={50} {...axis} /><Tooltip content={<ChartTooltip formatter={(value) => Number(value).toFixed(3)} />} />
        {Number.isFinite(low) && Number.isFinite(high) && <ReferenceArea x1={low} x2={high} fill="#397496" fillOpacity={0.08} />}
        <Bar dataKey="density" name="Posterior density" fill="#287f80" fillOpacity={0.82} isAnimationActive={false}>
          {bins.map((bin) => <Cell key={bin.x} fill={bin.x >= low && bin.x <= high ? "#287f80" : "#7ba9a5"} />)}
        </Bar>
        {Number.isFinite(median) && <ReferenceLine x={median} stroke="#b75e55" strokeDasharray="4 4" />}
      </ComposedChart>
    </ResponsiveContainer></div>
  );
}

export function BayesianPage() {
  const { data, loading, error } = useResource("/posterior");
  const [result, setResult] = useState(null);
  const [parameter, setParameter] = useState("growth_rate_day");
  const [distributionRefresh, setDistributionRefresh] = useState(0);
  const [running, setRunning] = useState(false);
  const [actionError, setActionError] = useState("");
  const current = result || data;
  const { data: distribution, loading: distributionLoading, error: distributionError } = useResource(
    `/posterior/distribution/${parameter}`,
    distributionRefresh,
  );
  const runEstimation = async () => {
    setRunning(true);
    setActionError("");
    try {
      const estimate = await api("/bayesian/estimate", { method: "POST" });
      setResult(estimate);
      setDistributionRefresh((value) => value + 1);
    } catch (failure) {
      setActionError(failure.message);
    } finally {
      setRunning(false);
    }
  };
  return (
    <>
      <PageHeader eyebrow="Bayesian estimation" title="Parameter Posterior" description="Inspect the bundled Metropolis–Hastings posterior or explicitly run four fresh chains from local observations." action={
        <button className="button-primary" onClick={runEstimation} disabled={running}>
          {running ? <LoaderCircle className="spin" size={14} /> : <Play size={13} />}
          {running ? "Sampling four chains…" : "Run fresh estimation"}
        </button>
      } />
      <State loading={loading} error={error}>
        {current && <>
          {actionError && <div className="error-banner">{actionError}</div>}
          {running && <div className="callout">The four Metropolis–Hastings chains are running locally. This may take a few minutes on a laptop; the saved posterior remains available until the new run completes.</div>}
          <div className="grid grid-3">
            <Metric label="Retained posterior draws" value={Number(current.draw_count).toLocaleString()} note={current.fresh_estimate ? "Fresh in-memory estimate" : "Bundled posterior artifact"} />
            <Metric label="Mean chain acceptance" value={`${(Number(current.mean_acceptance_rate) * 100).toFixed(1)}%`} note="Sampler diagnostic, not model accuracy" accent="blue" />
            <Metric label="Estimated parameters" value={current.parameter_count} note="Truncated log-normal priors" accent="gold" />
          </div>
          <Panel className="section-spacer" title="Posterior summary" subtitle="Equal-tail 95% credible interval · conditional on this model, likelihood and prior">
            <div className="table-wrap">
              <table className="data-table"><thead><tr><th>Parameter</th><th className="numeric">Posterior mean</th><th className="numeric">Median</th><th className="numeric">95% interval: lower</th><th className="numeric">95% interval: upper</th></tr></thead>
                <tbody>{current.parameters.map((row) => <tr key={row.parameter}><td>{parameterLabels[row.parameter] || row.parameter}</td><td className="numeric">{Number(row.posterior_mean).toPrecision(4)}</td><td className="numeric">{Number(row.median).toPrecision(4)}</td><td className="numeric">{Number(row.credible_interval_2_5).toPrecision(4)}</td><td className="numeric">{Number(row.credible_interval_97_5).toPrecision(4)}</td></tr>)}</tbody>
              </table>
            </div>
          </Panel>
          <div className="grid grid-2 section-spacer">
            <Panel title="Effective sample size" subtitle="Estimated independent-draw equivalents after autocorrelation">
              <div className="diagnostic-list">{current.diagnostics.map((row) => <div className="diagnostic-item" key={row.parameter}>
                <div><span>{parameterLabels[row.parameter] || row.parameter}</span><strong>{Number(row.effective_sample_size).toFixed(0)}</strong></div>
                <div className="diagnostic-bar"><span style={{ width: `${Math.min(100, Number(row.effective_sample_size) / Math.max(...current.diagnostics.map((item) => Number(item.effective_sample_size))) * 100)}%` }} /></div>
              </div>)}</div>
            </Panel>
            <Panel title="Split R-hat" subtitle="Between-chain distribution diagnostic; values near 1 indicate similar sampled distributions">
              <div className="diagnostic-list">{current.diagnostics.map((row) => <div className="diagnostic-item" key={row.parameter}>
                <div><span>{parameterLabels[row.parameter] || row.parameter}</span><strong>{Number(row.split_rhat).toFixed(3)}</strong></div>
                <div className="diagnostic-bar"><span className={Number(row.split_rhat) > 1.05 ? "bar-warn" : ""} style={{ width: `${Math.min(100, Number(row.split_rhat) / 1.1 * 100)}%` }} /></div>
              </div>)}</div>
            </Panel>
          </div>
          <Panel className="section-spacer" title="Posterior distribution" subtitle={parameterUnits[parameter] || parameter} action={
            <select className="select-control" value={parameter} onChange={(event) => setParameter(event.target.value)} aria-label="Posterior parameter">
              {current.parameters.map((row) => <option key={row.parameter} value={row.parameter}>{parameterLabels[row.parameter] || row.parameter}</option>)}
            </select>
          }>
            <State loading={distributionLoading} error={distributionError}>
              <ParameterHistogram distribution={distribution} />
            </State>
            <div className="chart-legend"><span className="legend-item"><i style={{ background: "#287f80" }} /> Posterior draws within 95% interval</span><span className="legend-item"><i style={{ background: "#b75e55" }} /> Posterior median</span></div>
          </Panel>
          <div className="callout">ESS and split R-hat are diagnostics, not proof of convergence. Interpret them cautiously because the posterior is conditioned on only 11 paired observation dates.</div>
        </>}
      </State>
    </>
  );
}

function PredictionTooltip({ active, payload, year }) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  const date = new Date(new Date(`${year}-01-01T00:00:00`).getTime() + Number(row.day) * 86400000);
  return (
    <div className="chart-tooltip">
      <div className="tooltip-date">{date.toLocaleDateString("en", { day: "2-digit", month: "short" })}</div>
      <div className="tooltip-line"><i style={{ background: "#287f80" }} /><span>Posterior median</span><strong>{Number(row.median_chlorophyll_mg_m3).toFixed(3)} mg/m³</strong></div>
      <div className="tooltip-line"><i style={{ background: "#6ba6a1" }} /><span>95% interval</span><strong>{Number(row.lower_95).toFixed(3)}–{Number(row.upper_95).toFixed(3)}</strong></div>
      {row.observed != null && <div className="tooltip-line"><i style={{ background: "#b75e55" }} /><span>Observed</span><strong>{Number(row.observed).toFixed(3)} mg/m³</strong></div>}
    </div>
  );
}

export function PredictionPage() {
  const { data: predictive, loading, error } = useResource("/prediction-uncertainty");
  const { data: observations, loading: observationsLoading, error: observationsError } = useResource("/observations");
  const predicted = predictive?.rows || [];
  const measured = observations?.rows || [];
  const referenceYear = measured.length ? Number(measured[0].date.slice(0, 4)) : 2003;
  const chartRows = useMemo(() => {
    const observedByDay = new Map(measured.map((row) => [
      Math.round((new Date(`${row.date}T00:00:00`) - new Date(`${referenceYear}-01-01T00:00:00`)) / 86400000),
      Number(row.chlorophyll_mg_m3),
    ]));
    return predicted.map((row) => ({ ...row, observed: observedByDay.get(Number(row.day)) ?? null }));
  }, [predicted, measured, referenceYear]);
  return (
    <>
      <PageHeader eyebrow="Prediction" title="Prediction & Uncertainty" description="Compare bundled satellite observations with the saved posterior predictive median and parameter-only 95% interval." />
      <State loading={loading || observationsLoading} error={error || observationsError}>
        {chartRows.length > 0 && <>
          <div className="grid grid-3">
            <Metric label="Prediction draws" value={predicted.length} note="Daily model output" />
            <Metric label="Observed dates" value={measured.length} note="Red markers are measured chlorophyll-a" accent="blue" />
            <Metric label="Uncertainty scope" value="Parameters" note="Excludes measurement and structural error" accent="gold" />
          </div>
          <Panel className="section-spacer" title="Observed and model-based chlorophyll-a" subtitle={`Posterior predictive output · reference year ${referenceYear} · mg/m³`}>
            <div className="chart-wrap tall"><ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartRows} margin={{ top: 10, right: 15, bottom: 4, left: 0 }}>
                {grid}<XAxis dataKey="day" tickFormatter={(day) => new Date(new Date(`${referenceYear}-01-01T00:00:00`).getTime() + Number(day) * 86400000).toLocaleDateString("en", { month: "short" })} minTickGap={26} {...axis} />
                <YAxis width={47} domain={[0, "auto"]} {...axis} /><Tooltip content={<PredictionTooltip year={referenceYear} />} />
                <Area type="monotone" dataKey="lower_95" name="Lower interval bound" stroke="none" fill="#287f80" fillOpacity={0} stackId="interval" />
                <Area type="monotone" dataKey={(row) => Math.max(0, Number(row.upper_95) - Number(row.lower_95))} name="95% parameter interval" stroke="none" fill="#6ba6a1" fillOpacity={0.19} stackId="interval" />
                <Line type="monotone" dataKey="median_chlorophyll_mg_m3" name="Posterior median" stroke="#287f80" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="observed" name="Satellite observations" stroke="#b75e55" strokeWidth={0} dot={{ r: 4, fill: "#b75e55", stroke: "#fff", strokeWidth: 1 }} connectNulls={false} />
              </ComposedChart>
            </ResponsiveContainer></div>
          </Panel>
          <div className="chart-legend"><span className="legend-item"><i style={{ background: "#b75e55" }} /> Satellite observations</span><span className="legend-item"><i style={{ background: "#287f80" }} /> Posterior median</span><span className="legend-item"><i style={{ background: "#6ba6a1" }} /> 95% parameter interval</span></div>
          <div className="callout warn">The shaded interval propagates parameter uncertainty only. It excludes satellite retrieval error, model structural error and uncertainty in unobserved MLD/PAR. This is not a future forecast.</div>
        </>}
      </State>
    </>
  );
}

export function LimitationsPage() {
  const { data: metadata, loading: metadataLoading, error: metadataError } = useResource("/metadata");
  const { data: posterior, loading, error } = useResource("/posterior");
  return (
    <>
      <PageHeader eyebrow="Reference" title="Results & Limitations" description="Evidence and uncertainty are presented with the scope needed to interpret this academic model responsibly." />
      <State loading={metadataLoading || loading} error={metadataError || error}>
        {metadata && posterior && <>
          <div className="grid grid-3">
            <Metric label="Observed paired dates" value={metadata.observation_count} note={`${metadata.start_date.slice(0, 4)} · September absent`} />
            <Metric label="Posterior draws" value={Number(posterior.draw_count).toLocaleString()} note={posterior.fresh_estimate ? "Fresh run" : "Bundled run"} accent="blue" />
            <Metric label="Mean acceptance rate" value={`${(Number(posterior.mean_acceptance_rate) * 100).toFixed(1)}%`} note="Sampler diagnostic, not model fit accuracy" accent="gold" />
          </div>
          <div className="grid grid-2 section-spacer">
            <Panel title="Posterior parameter summary" subtitle="Point estimates and equal-tail credible intervals">
              <div className="table-wrap"><table className="data-table"><thead><tr><th>Parameter</th><th className="numeric">Median</th><th className="numeric">95% interval</th></tr></thead><tbody>
                {posterior.parameters.map((row) => <tr key={row.parameter}><td>{parameterLabels[row.parameter] || row.parameter}</td><td className="numeric">{Number(row.median).toPrecision(4)}</td><td className="numeric">{Number(row.credible_interval_2_5).toPrecision(3)} – {Number(row.credible_interval_97_5).toPrecision(3)}</td></tr>)}
              </tbody></table></div>
            </Panel>
            <Panel title="Sampling diagnostics" subtitle="Descriptive summaries; not proof of convergence">
              <div className="table-wrap"><table className="data-table"><thead><tr><th>Parameter</th><th className="numeric">ESS</th><th className="numeric">Split R-hat</th></tr></thead><tbody>
                {posterior.diagnostics.map((row) => <tr key={row.parameter}><td>{parameterLabels[row.parameter] || row.parameter}</td><td className="numeric">{Number(row.effective_sample_size).toFixed(1)}</td><td className="numeric">{Number(row.split_rhat).toFixed(3)}</td></tr>)}
              </tbody></table></div>
            </Panel>
          </div>
          <div className="grid grid-2 section-spacer">
            <Panel title="What this project demonstrates"><ul className="bullet-list">
              <li>Loads real bundled JRC MODIS-Aqua chlorophyll and NOAA OISST observations with source-file provenance.</li>
              <li>Integrates a temperature-driven NPZD model using a documented seasonal-light assumption.</li>
              <li>Samples a Bayesian posterior using random-walk Metropolis–Hastings and reports uncertainty.</li>
            </ul></Panel>
            <Panel title="Interpretation limits"><ul className="bullet-list">{metadata.limitations.map((item) => <li key={item}>{item}</li>)}
              <li>Only 11 paired dates are available; parameter estimates may be weakly identified and intervals are broad.</li>
              <li>This simplified academic implementation is not a reproduction of the referenced paper's PMCMC workflow.</li>
            </ul></Panel>
          </div>
        </>}
      </State>
    </>
  );
}
