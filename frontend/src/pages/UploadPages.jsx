import { useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, FileUp, LoaderCircle, Play, Trash2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useUploadedDataset } from "../App";
import { ChartTooltip, dateLabel, Metric, PageHeader, Panel, State, useResource } from "../components";

const axis = { axisLine: false, tickLine: false, tick: { fill: "#82949c", fontSize: 9 } };
const grid = <CartesianGrid stroke="#e9eff1" vertical={false} />;

function downloadTemplate() {
  const blob = new Blob(["date,sst_c,chlorophyll_mg_m3\r\n"], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "oceansense_observations_template.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function UploadPage() {
  const { upload, setUpload } = useUploadedDataset();
  const [rows, setRows] = useState([]);
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    if (!upload) {
      setRows([]);
      return () => { active = false; };
    }
    setLoadingSaved(true);
    api(`/uploads/${encodeURIComponent(upload.upload_id)}`).then((result) => {
      if (active) setRows(result.rows);
    }).catch((failure) => {
      if (active) {
        setError(failure.message);
        setUpload(null);
      }
    }).finally(() => active && setLoadingSaved(false));
    return () => { active = false; };
  }, [upload?.upload_id]);

  const onFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setMessage("");
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/uploads", { method: "POST", body: form });
      setUpload({ upload_id: result.upload_id, filename: result.filename, count: result.count });
      setRows(result.rows);
      setMessage(`${result.count} observation records validated successfully.`);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const removeUpload = async () => {
    if (!upload) return;
    try {
      await api(`/uploads/${encodeURIComponent(upload.upload_id)}`, { method: "DELETE" });
    } catch (failure) {
      if (!failure.message.includes("not found")) setError(failure.message);
    }
    setUpload(null);
    setRows([]);
    setMessage("");
  };

  return (
    <>
      <PageHeader eyebrow="Forecasting" title="Dataset Upload" description="Validate a local CSV for interactive analysis. Uploaded records are held in API memory for this session and never replace bundled observations." action={<button className="button-secondary" onClick={downloadTemplate}><ArrowDownToLine size={14} /> Download template</button>} />
      <div className="grid grid-2">
        <Panel title="Upload observation CSV" subtitle="Required fields: date, sst_c, chlorophyll_mg_m3">
          <label className="drop-zone">
            {uploading ? <LoaderCircle size={22} className="spin" /> : <FileUp size={22} />}
            <strong>{uploading ? "Validating CSV…" : "Choose a CSV file"}</strong>
            <span>Maximum 5 MB · one unique date per row · no missing or non-finite values</span>
            <input className="file-control" aria-label="Choose CSV file" type="file" accept=".csv,text/csv" onChange={onFile} disabled={uploading} />
          </label>
          {error && <div role="alert" className="error-banner">{error}</div>}
          {message && <div className="success-banner">{message}</div>}
          <div className="callout">The uploaded chlorophyll column is shown only as an observed comparison. It does not update or fit the bundled Bayesian posterior.</div>
        </Panel>
        <Panel title="Validation rules">
          <ul className="bullet-list">
            <li>Dates must be valid, timezone-free date strings and unique by day.</li>
            <li>SST and chlorophyll columns must contain finite numeric values.</li>
            <li>Chlorophyll concentration cannot be negative.</li>
            <li>Maximum 10,000 rows per upload; files above 5 MB are rejected.</li>
            <li>Bundled source data remain unchanged; upload data is kept separately in memory.</li>
          </ul>
        </Panel>
      </div>
      {upload && <Panel className="section-spacer" title="Validated upload preview" subtitle={`${upload.filename} · ${upload.count} rows`} action={<button className="button-secondary" onClick={removeUpload}><Trash2 size={13} /> Remove upload</button>}>
        {loadingSaved ? <div className="state-box"><LoaderCircle className="spin" size={16} /> Loading uploaded rows…</div> : <div className="table-wrap">
          <table className="data-table"><thead><tr><th>Date</th><th className="numeric">SST (°C)</th><th className="numeric">Chlorophyll-a (mg/m³)</th></tr></thead>
            <tbody>{rows.slice(0, 10).map((row) => <tr key={row.date}><td>{row.date}</td><td className="numeric">{Number(row.sst_c).toFixed(2)}</td><td className="numeric">{Number(row.chlorophyll_mg_m3).toFixed(3)}</td></tr>)}</tbody>
          </table>
          {rows.length > 10 && <p className="muted-note">Showing the first 10 of {rows.length} validated rows.</p>}
        </div>}
      </Panel>}
    </>
  );
}

function PredictionComparison({ prediction }) {
  const observed = prediction.observed_chlorophyll_mg_m3;
  const estimate = {
    label: "Model prediction",
    value: Number(prediction.median),
    interval: [
      Number(prediction.median) - Number(prediction.lower_95),
      Number(prediction.upper_95) - Number(prediction.median),
    ],
  };
  const chartData = [
    ...(Number.isFinite(observed) ? [{ label: "Observed", value: observed, interval: [0, 0] }] : []),
    estimate,
  ];
  return (
    <div className="chart-wrap compact"><ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} margin={{ top: 10, right: 12, bottom: 3, left: 3 }}>
        {grid}<XAxis dataKey="label" {...axis} /><YAxis width={48} domain={[0, "auto"]} unit=" mg/m³" {...axis} />
        <Tooltip content={<ChartTooltip formatter={(value) => `${Number(value).toFixed(3)} mg/m³`} />} />
        <Bar dataKey="value" name="Chlorophyll-a" maxBarSize={46}>
          <Cell fill="#b75e55" /><Cell fill="#287f80" />
          <ErrorBar dataKey="interval" direction="y" width={5} stroke="#24475b" />
        </Bar>
      </BarChart>
    </ResponsiveContainer></div>
  );
}

export function InteractivePredictionPage() {
  const { upload } = useUploadedDataset();
  const [source, setSource] = useState("bundled");
  const [targetDate, setTargetDate] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [running, setRunning] = useState(false);
  const [actionError, setActionError] = useState("");
  const path = source === "uploaded" && upload ? `/uploads/${encodeURIComponent(upload.upload_id)}` : "/observations";
  const { data, loading, error } = useResource(path);
  const rows = data?.rows || [];

  useEffect(() => {
    if (rows.length && !rows.some((row) => row.date === targetDate)) {
      setTargetDate(rows[0].date);
      setPrediction(null);
    }
  }, [rows, targetDate]);

  const selected = rows.find((row) => row.date === targetDate);
  const yearRows = useMemo(() => rows.filter((row) => row.date?.slice(0, 4) === targetDate.slice(0, 4)), [rows, targetDate]);

  const runPrediction = async () => {
    if (!targetDate) return;
    setRunning(true);
    setActionError("");
    setPrediction(null);
    try {
      const result = await api("/predictions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset: source,
          target_date: targetDate,
          upload_id: source === "uploaded" ? upload?.upload_id : null,
        }),
      });
      setPrediction(result);
    } catch (failure) {
      setActionError(failure.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow="Forecasting" title="Interactive Prediction" description="Run the existing posterior predictive calculation for a selected observed date. The result is a model estimate, not a future forecast." />
      <State loading={loading} error={source === "uploaded" && !upload ? "Upload and validate a CSV in Dataset Upload before selecting uploaded data." : error}>
        {rows.length > 0 && <>
          <Panel title="Select data and observation date" subtitle="The chosen date must have at least two SST observations in its calendar year">
            <div className="form-row">
              <div className="form-field"><label htmlFor="prediction-dataset">Dataset</label>
                <select id="prediction-dataset" className="select-control" value={source} onChange={(event) => { setSource(event.target.value); setPrediction(null); }}>
                  <option value="bundled">Bundled observations</option>
                  {upload && <option value="uploaded">Uploaded: {upload.filename}</option>}
                </select>
              </div>
              <div className="form-field"><label htmlFor="prediction-date">Observation date</label>
                <select id="prediction-date" className="select-control" value={targetDate} onChange={(event) => { setTargetDate(event.target.value); setPrediction(null); }}>
                  {rows.map((row) => <option key={row.date} value={row.date}>{dateLabel(row.date)}</option>)}
                </select>
              </div>
              <button className="button-primary" onClick={runPrediction} disabled={running || yearRows.length < 2}>
                {running ? <LoaderCircle className="spin" size={14} /> : <Play size={13} />}
                {running ? "Calculating…" : "Run prediction"}
              </button>
            </div>
            {selected && <div className="grid grid-2 section-spacer">
              <Metric label="Observed SST" value={`${Number(selected.sst_c).toFixed(2)} °C`} note="Selected date" accent="blue" />
              <Metric label="Observed chlorophyll-a" value={`${Number(selected.chlorophyll_mg_m3).toFixed(3)} mg/m³`} note="Shown for comparison; not used to fit posterior" />
            </div>}
            {yearRows.length < 2 && <div className="callout warn">At least two SST observations in the selected calendar year are needed to provide interpolated model forcing.</div>}
            {actionError && <div role="alert" className="error-banner">{actionError}</div>}
          </Panel>
          {prediction && <div className="grid grid-2 section-spacer">
            <Panel title={`Model estimate · ${dateLabel(prediction.target_date)}`} subtitle="Posterior median with equal-tail 95% parameter interval">
              <div className="grid grid-3">
                <Metric label="Predicted median" value={`${Number(prediction.median).toFixed(3)} mg/m³`} />
                <Metric label="Lower 95%" value={`${Number(prediction.lower_95).toFixed(3)}`} accent="blue" />
                <Metric label="Upper 95%" value={`${Number(prediction.upper_95).toFixed(3)}`} accent="gold" />
              </div>
              <PredictionComparison prediction={prediction} />
            </Panel>
            <Panel title="How to interpret this estimate">
              <div className="stat-list">
                <div><span>Temperature forcing</span><strong>{prediction.observed_sst_c == null ? "Interpolated from SST" : `${Number(prediction.observed_sst_c).toFixed(2)} °C observed`}</strong></div>
                <div><span>Observed value</span><strong>{prediction.observed_chlorophyll_mg_m3 == null ? "No exact date match" : `${Number(prediction.observed_chlorophyll_mg_m3).toFixed(3)} mg/m³`}</strong></div>
                <div><span>Interval scope</span><strong>Parameter uncertainty only</strong></div>
                <div><span>Forecast horizon</span><strong>Observed date, not future</strong></div>
              </div>
              <div className="callout warn">Uploaded chlorophyll is not used to update the posterior. Uploaded SST drives the existing NPZD temperature forcing; uncertainty excludes retrieval and structural model error.</div>
            </Panel>
          </div>}
        </>}
      </State>
    </>
  );
}
