import { useEffect, useState } from "react";
import { fetchResource } from "./api";
import { AlertCircle, LoaderCircle } from "lucide-react";

export function useResource(path, refreshKey = 0) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    fetchResource(path).then((result) => {
      if (active) setData(result);
    }).catch((failure) => {
      if (active) setError(failure.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [path, refreshKey]);

  return { data, loading, error };
}

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="page-action">{action}</div>}
    </div>
  );
}

export function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && (
        <div className="panel-heading">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Metric({ label, value, note, accent = "teal" }) {
  return (
    <div className={`metric metric-${accent}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note && <div className="metric-note">{note}</div>}
    </div>
  );
}

export function State({ loading, error, children }) {
  if (loading) {
    return <div className="state-box"><LoaderCircle className="spin" size={18} /> Loading local project data…</div>;
  }
  if (error) {
    return <div className="state-box error-state"><AlertCircle size={18} /><span>{error}</span></div>;
  }
  return children;
}

export function EmptyState({ children }) {
  return <div className="empty-state">{children}</div>;
}

export function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="tooltip-date">{label}</div>
      {payload.map((item) => (
        <div className="tooltip-line" key={item.dataKey}>
          <i style={{ backgroundColor: item.color }} />
          <span>{item.name}</span>
          <strong>{formatter ? formatter(item.value, item.dataKey) : Number(item.value).toLocaleString(undefined, { maximumFractionDigits: 3 })}</strong>
        </div>
      ))}
    </div>
  );
}

export const parameterLabels = {
  growth_rate_day: "Phytoplankton growth",
  grazing_rate_day: "Zooplankton grazing",
  zooplankton_mortality_day: "Zooplankton mortality",
  chlorophyll_scale_mg_m3: "Chlorophyll scale",
  observation_log_sd: "Observation log-SD",
};

export const parameterUnits = {
  growth_rate_day: "Growth rate (day⁻¹)",
  grazing_rate_day: "Grazing rate (day⁻¹)",
  zooplankton_mortality_day: "Mortality rate (day⁻¹)",
  chlorophyll_scale_mg_m3: "Chlorophyll scale (mg/m³ per relative P)",
  observation_log_sd: "Observation log-SD",
};

export const dateLabel = (value) => new Date(`${value}T00:00:00`).toLocaleDateString("en", {
  day: "2-digit", month: "short", year: "numeric",
});
