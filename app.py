"""Offline Streamlit dashboard for the OceanSense AI academic project."""

import hashlib
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.model import (
    NPZDParameters,
    load_observations,
    posterior_predictive,
    posterior_summary,
    run_bayesian_estimation,
    sampling_diagnostics,
    simulate_npzd,
)
from src.interactive import posterior_prediction_for_date, validate_uploaded_csv


ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
COLORS = {
    "navy": "#123247",
    "teal": "#287f80",
    "blue": "#397496",
    "gold": "#b37a35",
    "coral": "#b75e55",
    "slate": "#627783",
    "grid": "#e3eaee",
    "text": "#203947",
}
STATE_COLORS = [COLORS["navy"], COLORS["teal"], COLORS["gold"], COLORS["blue"]]
PARAMETER_LABELS = {
    "growth_rate_day": "Phytoplankton growth",
    "grazing_rate_day": "Zooplankton grazing",
    "zooplankton_mortality_day": "Zooplankton mortality",
    "chlorophyll_scale_mg_m3": "Chlorophyll scale",
    "observation_log_sd": "Observation log-SD",
}
PARAMETER_UNITS = {
    "growth_rate_day": "Growth rate (day⁻¹)",
    "grazing_rate_day": "Grazing rate (day⁻¹)",
    "zooplankton_mortality_day": "Mortality rate (day⁻¹)",
    "chlorophyll_scale_mg_m3": "Chlorophyll scale (mg/m³ per relative P)",
    "observation_log_sd": "Observation log-SD",
}
NAVIGATION_GROUPS = {
    "Overview": ["Project Overview"],
    "Data Analysis": [
        "Dataset Explorer",
        "Ocean Observation Analysis",
        "SST Analysis",
        "Chlorophyll-a Analysis",
        "Dataset Upload",
    ],
    "Ecosystem Modelling": ["NPZD Ecosystem Model"],
    "Bayesian Estimation": ["Bayesian Parameter Estimation"],
    "Predictions": [
        "Interactive Prediction",
        "Prediction and Uncertainty Analysis",
    ],
    "Results": ["Results and Model Limitations"],
}

st.set_page_config(page_title="OceanSense AI", page_icon="O", layout="wide")
st.markdown(
    """
    <style>
    :root {
        color-scheme: light;
        --ink: #203947;
        --muted: #627783;
        --navy: #123247;
        --teal: #287f80;
        --ocean: #397496;
        --canvas: #f3f6f7;
        --line: #e1e8ec;
        --surface: #ffffff;
    }
    .stApp {
        background: var(--canvas);
        color: var(--ink);
    }
    [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 1500px;
        padding: 1.6rem 2.5rem 3.2rem;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0;
    }
    h1, h2, h3 {
        color: var(--navy);
        letter-spacing: -0.025em;
    }
    h1 {
        font-size: 2.15rem;
        font-weight: 720;
        margin-bottom: 0.35rem;
    }
    h2, h3 {
        font-weight: 680;
    }
    h2 {
        margin-top: 0.65rem;
        margin-bottom: 0.5rem;
    }
    h3 {
        margin-top: 0.8rem;
        margin-bottom: 0.45rem;
    }
    [data-testid="stCaptionContainer"] {
        color: var(--muted);
        line-height: 1.55;
    }
    section[data-testid="stSidebar"] {
        background: #112d3d;
        border-right: 1px solid #254353;
    }
    section[data-testid="stSidebar"] > div:first-child {
        background: #112d3d;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding: 0.65rem 0.7rem 1rem;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #c8d6dd;
    }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.65rem 0.35rem 1.25rem;
        border-bottom: 1px solid rgba(226, 238, 244, 0.12);
        margin-bottom: 0.8rem;
    }
    .brand-mark {
        display: grid;
        place-items: center;
        width: 2.3rem;
        height: 2.3rem;
        border: 1px solid rgba(214, 235, 239, 0.38);
        border-radius: 0.65rem;
        color: #e3f1ef;
        font-size: 1.15rem;
        font-weight: 750;
        letter-spacing: -0.06em;
    }
    .brand-name {
        color: #f2f6f7;
        font-size: 0.96rem;
        font-weight: 720;
        letter-spacing: -0.02em;
    }
    .brand-subtitle {
        color: #9fb3be;
        font-size: 0.62rem;
        letter-spacing: 0.11em;
        margin-top: 0.13rem;
        text-transform: uppercase;
    }
    .sidebar-section-label {
        color: #8fa8b5;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.13em;
        margin: 0.9rem 0 0.35rem;
        padding-left: 0.65rem;
        text-transform: uppercase;
    }
    section[data-testid="stSidebar"] [data-testid="stButton"] {
        margin: 0;
    }
    section[data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height: 2.15rem;
        justify-content: flex-start;
        margin: 0.08rem 0;
        padding: 0.38rem 0.68rem;
        text-align: left;
        transition: background-color 120ms ease, color 120ms ease;
    }
    section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {
        background: transparent;
        border: 1px solid transparent;
        color: #d2dfe5;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]:hover {
        background: #1b3c4d;
        border-color: #315466;
        color: #ffffff;
    }
    section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
        background: #205b68;
        border: 1px solid #337786;
        border-left: 3px solid #65b5ad;
        color: #ffffff;
        font-weight: 650;
    }
    .sidebar-footer {
        border-top: 1px solid rgba(226, 238, 244, 0.12);
        color: #9fb3be;
        font-size: 0.72rem;
        line-height: 1.5;
        margin-top: 1.2rem;
        padding: 0.8rem 0.45rem 0.15rem;
    }
    .page-context {
        align-items: center;
        color: #778a95;
        display: flex;
        font-size: 0.68rem;
        font-weight: 650;
        gap: 0.55rem;
        letter-spacing: 0.1em;
        margin: 0.05rem 0 0.9rem;
        text-transform: uppercase;
    }
    .page-context span {
        color: var(--teal);
    }
    .overview-hero {
        align-items: center;
        background: var(--navy);
        border: 1px solid #1d4356;
        border-radius: 16px;
        color: #f3f7f8;
        display: flex;
        justify-content: space-between;
        margin: 0.15rem 0 1.1rem;
        min-height: 170px;
        padding: 1.7rem 2rem;
    }
    .overview-hero h1 {
        color: #ffffff;
        font-size: 2.45rem;
        letter-spacing: -0.045em;
        margin: 0.4rem 0 0.3rem;
    }
    .overview-hero p {
        color: #ccdae0;
        font-size: 0.97rem;
        line-height: 1.55;
        margin: 0;
        max-width: 680px;
    }
    .hero-eyebrow, .eyebrow {
        color: #83c1bb;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }
    .hero-period {
        border-left: 1px solid rgba(231, 240, 243, 0.22);
        margin-left: 2rem;
        min-width: 170px;
        padding-left: 1.5rem;
    }
    .hero-period strong {
        color: #ffffff;
        display: block;
        font-size: 1.5rem;
        font-weight: 680;
        margin: 0.35rem 0 0.1rem;
    }
    .hero-period span {
        color: #bbccd4;
        font-size: 0.78rem;
    }
    .overview-section-title {
        color: var(--navy);
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.015em;
        margin: 0.5rem 0 0.15rem;
    }
    .overview-section-note {
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.5;
        margin-bottom: 0.7rem;
    }
    .overview-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        color: var(--ink);
        height: 100%;
        line-height: 1.55;
        padding: 1rem 1.05rem;
    }
    .overview-card + .overview-card {
        margin-top: 0.7rem;
    }
    .overview-card-title {
        color: var(--navy);
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .overview-card p {
        color: var(--muted);
        font-size: 0.78rem;
        margin: 0;
    }
    .workflow-step {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 11px;
        min-height: 92px;
        padding: 0.9rem 1rem;
    }
    .workflow-step span {
        color: var(--teal);
        display: block;
        font-size: 0.65rem;
        font-weight: 750;
        letter-spacing: 0.12em;
        margin-bottom: 0.3rem;
        text-transform: uppercase;
    }
    .workflow-step strong {
        color: var(--navy);
        display: block;
        font-size: 0.83rem;
        margin-bottom: 0.18rem;
    }
    .workflow-step p {
        color: var(--muted);
        font-size: 0.74rem;
        line-height: 1.45;
        margin: 0;
    }
    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-top: 2px solid #b6d2d1;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(18, 50, 71, 0.035);
        min-height: 105px;
        padding: 0.9rem 1rem;
    }
    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 650;
    }
    [data-testid="stMetricValue"] {
        color: var(--navy);
        font-size: 1.42rem;
        font-weight: 720;
    }
    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 11px;
        box-shadow: 0 2px 6px rgba(18, 50, 71, 0.035);
        overflow: hidden;
    }
    [data-testid="stDataFrame"] {
        padding: 0.15rem;
    }
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 650;
        min-height: 2.45rem;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button {
        background: var(--teal);
        border: 1px solid var(--teal);
        color: #ffffff;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button:hover {
        background: #216d6e;
        border-color: #216d6e;
        color: #ffffff;
    }
    [data-baseweb="select"] > div,
    [data-testid="stFileUploader"] section {
        border-color: #ccd9df;
        border-radius: 8px;
    }
    [data-testid="stAlert"] {
        border: 1px solid var(--line);
        border-radius: 9px;
    }
    hr {
        border-color: var(--line);
        margin: 1.25rem 0;
    }
    @media (max-width: 800px) {
        [data-testid="stAppViewContainer"] .main .block-container {
            padding: 1rem 1rem 2rem;
        }
        h1 {
            font-size: 1.8rem;
        }
        .overview-hero {
            align-items: center;
            gap: 0.65rem;
            min-height: 0;
            padding: 1rem;
        }
        .overview-hero h1 {
            font-size: 1.8rem;
        }
        .overview-hero p {
            font-size: 0.82rem;
        }
        .hero-period {
            border-left: 1px solid rgba(231, 240, 243, 0.22);
            border-top: 0;
            margin-left: 0.35rem;
            min-width: 140px;
            padding: 0.3rem 0 0.3rem 0.75rem;
        }
        .hero-period strong {
            font-size: 0.95rem;
            white-space: nowrap;
        }
        [data-testid="stMetric"] {
            min-height: 88px;
            padding: 0.75rem;
        }
    }
    @media (max-width: 480px) {
        .overview-hero {
            align-items: flex-start;
            flex-direction: column;
            gap: 0.75rem;
        }
        .hero-period {
            border-left: 0;
            border-top: 1px solid rgba(231, 240, 243, 0.22);
            margin-left: 0;
            padding: 0.65rem 0 0;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def style_figure(figure: go.Figure, height: int = 430) -> go.Figure:
    figure.update_layout(
        template="plotly_white",
        colorway=[COLORS["navy"], COLORS["teal"], COLORS["gold"], COLORS["blue"], COLORS["coral"]],
        font={"family": "Segoe UI, sans-serif", "color": COLORS["text"], "size": 11},
        title={"x": 0.025, "xanchor": "left", "font": {"size": 16, "color": COLORS["navy"]}},
        margin={"l": 38, "r": 26, "t": 64, "b": 38},
        height=height,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#ffffff",
        hoverlabel={"bgcolor": "#ffffff", "font": {"color": COLORS["text"]}},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 10},
        },
    )
    figure.update_xaxes(
        showline=True,
        linecolor=COLORS["grid"],
        gridcolor=COLORS["grid"],
        zeroline=False,
        tickfont={"color": COLORS["slate"]},
        title_font={"color": COLORS["slate"]},
    )
    figure.update_yaxes(
        showline=False,
        gridcolor=COLORS["grid"],
        zeroline=False,
        tickfont={"color": COLORS["slate"]},
        title_font={"color": COLORS["slate"]},
    )
    return figure


def set_active_section(destination: str) -> None:
    st.session_state.active_section = destination


@st.cache_data
def observations() -> pd.DataFrame:
    return load_observations()


@st.cache_data
def saved_posterior() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "posterior_samples.csv")


@st.cache_data
def saved_predictive() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "posterior_predictive.csv")


@st.cache_data
def saved_diagnostics() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "posterior_diagnostics.csv")


@st.cache_data
def default_simulation(observation_data: pd.DataFrame) -> pd.DataFrame:
    return simulate_npzd(NPZDParameters(), observation_data)


def posterior() -> pd.DataFrame:
    return st.session_state.get("posterior", saved_posterior())


def predictive(data: pd.DataFrame) -> pd.DataFrame:
    return st.session_state.get("predictive", saved_predictive())


def run_mcmc(data: pd.DataFrame) -> None:
    with st.spinner("Running four Metropolis-Hastings chains from bundled observations..."):
        samples, acceptance = run_bayesian_estimation(data, draws=1200, burn_in=300, seed=2026, chains=4)
        st.session_state.posterior = samples
        st.session_state.predictive = posterior_predictive(samples, data, samples=100)
        st.session_state.acceptance = acceptance
        st.session_state.sampling_diagnostics = sampling_diagnostics(samples)


data = observations()
st.session_state.setdefault("active_section", "Project Overview")
active_section = st.session_state.active_section

st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="brand-mark">O</div>
        <div>
            <div class="brand-name">OceanSense AI</div>
            <div class="brand-subtitle">Marine research dashboard</div>
        </div>
    </div>
    <div class="sidebar-section-label">Workspace</div>
    """,
    unsafe_allow_html=True,
)
for group, destinations in NAVIGATION_GROUPS.items():
    if group != "Overview":
        st.sidebar.markdown(
            f'<div class="sidebar-section-label">{group}</div>',
            unsafe_allow_html=True,
        )
    for destination in destinations:
        key = "navigate_" + "_".join(destination.lower().split())
        st.sidebar.button(
            destination,
            key=key,
            type="primary" if destination == active_section else "secondary",
            use_container_width=True,
            on_click=set_active_section,
            args=(destination,),
        )
section = st.session_state.active_section
section_group = next(
    group for group, destinations in NAVIGATION_GROUPS.items() if section in destinations
)
st.sidebar.markdown(
    """
    <div class="sidebar-footer">
        Local analysis · no external services<br>
        Bundled observations with optional session uploads
    </div>
    """,
    unsafe_allow_html=True,
)

if section != "Project Overview":
    st.markdown(
        f'<div class="page-context"><span>{section_group}</span><span> / </span>{section}</div>',
        unsafe_allow_html=True,
    )

if section == "Project Overview":
    st.markdown(
        f"""
        <div class="overview-hero">
            <div>
                <div class="hero-eyebrow">Black Sea · Ocean observation system</div>
                <h1>OceanSense AI</h1>
                <p>Explore satellite-derived chlorophyll-a and sea-surface temperature
                alongside a transparent NPZD ecosystem model and Bayesian analysis.</p>
            </div>
            <div class="hero-period">
                <span>OBSERVATION WINDOW</span>
                <strong>{data.date.min():%b %Y}</strong>
                <span>through {data.date.max():%b %Y}</span>
                <span>Paired regional means</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    observation_count, chlorophyll_range, sst_range = st.columns(3)
    with observation_count:
        st.metric("Observation dates", f"{len(data)}")
        st.caption("Paired regional means")
    with chlorophyll_range:
        st.metric(
            "Chlorophyll-a range",
            f"{data.chlorophyll_mg_m3.min():.2f}–{data.chlorophyll_mg_m3.max():.2f}",
            help="mg/m³",
        )
        st.caption("mg/m³ · JRC EMIS MODIS-Aqua")
    with sst_range:
        st.metric(
            "SST range",
            f"{data.sst_c.min():.1f}–{data.sst_c.max():.1f}",
            help="°C",
        )
        st.caption("°C · NOAA OISST v2.1")

    chart_column, context_column = st.columns([1.8, 0.82], gap="large")
    with chart_column:
        st.markdown(
            '<div class="overview-section-title">Ocean conditions through the observation period</div>'
            '<div class="overview-section-note">Observed values only · each point is a paired satellite/SST date</div>',
            unsafe_allow_html=True,
        )
        overview_figure = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.16,
            subplot_titles=("Sea-surface temperature", "Chlorophyll-a concentration"),
        )
        overview_figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["sst_c"],
                mode="lines+markers",
                name="SST",
                line={"color": COLORS["blue"], "width": 2.4},
                marker={"size": 7, "color": COLORS["blue"]},
                hovertemplate="%{x|%d %b %Y}<br>SST: %{y:.2f} °C<extra></extra>",
            ),
            row=1,
            col=1,
        )
        overview_figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["chlorophyll_mg_m3"],
                mode="lines+markers",
                name="Chlorophyll-a",
                line={"color": COLORS["teal"], "width": 2.4},
                marker={"size": 7, "color": COLORS["teal"]},
                hovertemplate="%{x|%d %b %Y}<br>Chlorophyll-a: %{y:.3f} mg/m³<extra></extra>",
            ),
            row=2,
            col=1,
        )
        overview_figure.update_yaxes(title_text="°C", row=1, col=1)
        overview_figure.update_yaxes(title_text="mg/m³", rangemode="tozero", row=2, col=1)
        overview_figure.update_xaxes(
            title_text="Observation date",
            tickformat="%b",
            dtick="M2",
            range=[data.date.min(), data.date.max()],
            row=2,
            col=1,
        )
        overview_figure.update_layout(
            title="Measured Black Sea conditions",
            showlegend=False,
            hovermode="x unified",
        )
        overview_figure.update_annotations(font={"size": 11, "color": COLORS["slate"]})
        st.plotly_chart(style_figure(overview_figure, height=500), width="stretch")
        st.caption(
            "The connecting segments are visual guides between observations; they do not fill missing dates or represent daily measurements."
        )

    with context_column:
        st.markdown(
            """
            <div class="overview-section-title">Data at a glance</div>
            <div class="overview-section-note">Two independent observation products, paired by date.</div>
            <div class="overview-card">
                <div class="overview-card-title">Chlorophyll-a</div>
                <p>JRC EMIS Black Sea MODIS-Aqua product. Spatial means use valid positive pixels; coverage varies with cloud screening.</p>
            </div>
            <div class="overview-card">
                <div class="overview-card-title">Sea-surface temperature</div>
                <p>NOAA OISST v2.1 regional means in °C. OISST is a Level-4 analysis using satellite and in-situ inputs.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="overview-card">
                <div class="overview-card-title">Sampling coverage</div>
                <p>{len(data)} paired dates are available. September is absent from the bundled 2003 subset; no observation is fabricated for the gap.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="overview-section-title">Research workflow</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="overview-section-note">A reproducible path from measured observations to model-based interpretation.</div>',
        unsafe_allow_html=True,
    )
    observe, model, quantify = st.columns(3, gap="medium")
    with observe:
        st.markdown(
            '<div class="workflow-step"><span>01 · Observe</span><strong>Inspect the source data</strong><p>Review dates, regional means, source files, and coverage.</p></div>',
            unsafe_allow_html=True,
        )
    with model:
        st.markdown(
            '<div class="workflow-step"><span>02 · Model</span><strong>Explore NPZD dynamics</strong><p>Use observed SST forcing with the documented seasonal-light assumption.</p></div>',
            unsafe_allow_html=True,
        )
    with quantify:
        st.markdown(
            '<div class="workflow-step"><span>03 · Quantify</span><strong>Examine posterior uncertainty</strong><p>Review parameter estimates and date-specific posterior predictions.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        """<div class="overview-card" style="border-left:3px solid #b37a35; margin-top:0.9rem;"><div class="overview-card-title">Scientific scope</div><p>Mixed-layer depth and PAR are not bundled observations. Seasonal light is a model assumption; posterior predictions are conditional on this simplified NPZD model and are not future forecasts or independent validation.</p></div>""",
        unsafe_allow_html=True,
    )

elif section == "Dataset Explorer":
    st.subheader("Bundled processed observations")
    st.dataframe(
        data,
        width="stretch",
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn("Observation date", format="YYYY-MM-DD"),
            "chlorophyll_mg_m3": st.column_config.NumberColumn("Chlorophyll-a (mg/m³)", format="%.3f"),
            "chlorophyll_valid_pixels": st.column_config.NumberColumn("Valid pixels", format="%d"),
            "chlorophyll_source_file": st.column_config.TextColumn("Chlorophyll source file"),
            "sst_c": st.column_config.NumberColumn("SST (°C)", format="%.2f"),
            "sst_source_file": st.column_config.TextColumn("SST source file"),
        },
    )
    st.caption("Each row is a spatial mean for one observed date. The source-file columns link it to the bundled raw NetCDF inputs.")
    st.download_button("Download processed observations", data.to_csv(index=False), "black_sea_observations_2003.csv", "text/csv")
    st.subheader("Data provenance")
    st.markdown("""
    - Chlorophyll-a: JRC EMIS MODIS-Aqua daily Black Sea maps, `chlideachla`, mg/m³; spatial grid 40.75–47.48°N and 27.28–42.00°E. The CSV contains spatial means of valid positive pixels for selected 2003 dates.
    - SST: NOAA OISST v2.1 daily AVHRR-based Level 4 analysis, `sst`, Celsius; the CSV contains means over 40.5–48°N and 27–42°E for corresponding dates.
    - Each row identifies the exact local raw NetCDF files from which it was derived. No chart uses generated observations.
    """)

elif section == "Ocean Observation Analysis":
    st.subheader("Joint observations")
    figure = px.scatter(
        data,
        x="sst_c",
        y="chlorophyll_mg_m3",
        color="chlorophyll_valid_pixels",
        color_continuous_scale=["#d9efed", COLORS["teal"], COLORS["navy"]],
        hover_data={
            "date": "|%Y-%m-%d",
            "chlorophyll_valid_pixels": ":,",
            "chlorophyll_source_file": True,
            "sst_source_file": True,
        },
        labels={
            "sst_c": "SST (°C)",
            "chlorophyll_mg_m3": "Chlorophyll-a (mg/m³)",
            "chlorophyll_valid_pixels": "Valid chlorophyll pixels",
        },
        title="Observed chlorophyll-a versus sea-surface temperature",
    )
    figure.update_traces(marker={"size": 12, "line": {"width": 1.3, "color": "#ffffff"}})
    figure.update_coloraxes(colorbar_title="Valid pixels")
    st.plotly_chart(style_figure(figure), width="stretch")
    summary = data[["chlorophyll_mg_m3", "sst_c", "chlorophyll_valid_pixels"]].describe().T
    summary.index = ["Chlorophyll-a (mg/m³)", "SST (°C)", "Valid pixels"]
    st.dataframe(summary.style.format("{:,.2f}"), width="stretch")
    st.caption(f"Observed dates: {data.date.min():%Y-%m-%d} to {data.date.max():%Y-%m-%d}; n = {len(data)}")
    st.caption("Each point is a paired satellite chlorophyll and NOAA SST observation. Color indicates the chlorophyll valid-pixel count; the scatter does not imply causation.")

elif section == "SST Analysis":
    st.subheader("Real Black Sea SST")
    figure = px.line(
        data,
        x="date",
        y="sst_c",
        markers=True,
        hover_data={"date": "|%Y-%m-%d", "sst_c": ":.2f", "sst_source_file": True},
        labels={"date": "Observation date", "sst_c": "SST (°C)"},
        title="Observed monthly spatial-mean sea-surface temperature",
    )
    figure.update_traces(
        line={"color": COLORS["blue"], "width": 2.5},
        marker={"size": 9, "color": COLORS["blue"], "line": {"color": "#ffffff", "width": 1.5}},
    )
    figure.update_yaxes(title_text="Sea-surface temperature (°C)")
    st.plotly_chart(style_figure(figure), width="stretch")
    st.caption("Points show the bundled NOAA OISST v2.1 regional means. September 2003 is absent; the connecting line is a visual guide between observations, not an interpolated record.")
    st.caption("OISST is a Level-4 analysis using satellite and in-situ inputs, not a pure satellite-only series.")

elif section == "Chlorophyll-a Analysis":
    st.subheader("Real MODIS-Aqua chlorophyll-a")
    figure = px.line(
        data,
        x="date",
        y="chlorophyll_mg_m3",
        markers=True,
        hover_data={
            "date": "|%Y-%m-%d",
            "chlorophyll_mg_m3": ":.3f",
            "chlorophyll_valid_pixels": ":,",
            "chlorophyll_source_file": True,
        },
        labels={"date": "Observation date", "chlorophyll_mg_m3": "Chlorophyll-a (mg/m³)"},
        title="Observed JRC EMIS Black Sea chlorophyll-a",
    )
    figure.update_traces(
        line={"color": COLORS["teal"], "width": 2.5},
        marker={"size": 9, "color": COLORS["teal"], "line": {"color": "#ffffff", "width": 1.5}},
    )
    figure.update_yaxes(title_text="Chlorophyll-a (mg/m³)", rangemode="tozero")
    st.plotly_chart(style_figure(figure), width="stretch")
    coverage = px.bar(
        data,
        x="date",
        y="chlorophyll_valid_pixels",
        hover_data={"date": "|%Y-%m-%d", "chlorophyll_valid_pixels": ":,", "chlorophyll_source_file": True},
        labels={"date": "Observation date", "chlorophyll_valid_pixels": "Valid pixels"},
        title="Valid satellite pixels contributing to each mean",
    )
    coverage.update_traces(marker_color=COLORS["blue"])
    coverage.update_yaxes(title_text="Valid chlorophyll pixels")
    st.plotly_chart(style_figure(coverage, height=330), width="stretch")
    st.caption("The plotted concentrations are spatial means of valid positive satellite pixels. Pixel counts vary with cloud and quality screening; a lower count means less spatial coverage, not necessarily lower chlorophyll.")

elif section == "NPZD Ecosystem Model":
    st.subheader("Simplified NPZD model")
    st.markdown("The four panels show the model's **simulated** nutrient, phytoplankton, zooplankton, and detritus states. Real SST supplies temperature forcing; seasonal light remains a model assumption.")
    simulation = default_simulation(data)
    state_labels = {
        "nutrient": "Nutrient",
        "phytoplankton": "Phytoplankton",
        "zooplankton": "Zooplankton",
        "detritus": "Detritus",
    }
    figure = make_subplots(
        rows=2,
        cols=2,
        shared_xaxes=True,
        vertical_spacing=0.16,
        horizontal_spacing=0.12,
        subplot_titles=[state_labels[state] for state in state_labels],
    )
    for index, (state, label) in enumerate(state_labels.items()):
        row, column = divmod(index, 2)
        row += 1
        column += 1
        figure.add_trace(
            go.Scatter(
                x=simulation["day"],
                y=simulation[state],
                mode="lines",
                name=label,
                line={"color": STATE_COLORS[index], "width": 2.5},
                hovertemplate=f"Day %{{x}}<br>{label}: %{{y:.3f}} relative units<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=column,
        )
        figure.update_yaxes(title_text="Relative units", row=row, col=column)
    figure.update_xaxes(title_text="Day of year", row=2, col=1)
    figure.update_xaxes(title_text="Day of year", row=2, col=2)
    figure.update_layout(title="Daily NPZD simulation (default parameters)", showlegend=False)
    st.plotly_chart(style_figure(figure, height=610), width="stretch")
    st.caption("All four curves are numerical model states, not measured concentrations. Separate panels make their trajectories readable without implying that relative model units are directly comparable to satellite chlorophyll.")

elif section == "Bayesian Parameter Estimation":
    st.subheader("Metropolis-Hastings posterior")
    st.write("The bundled posterior and its diagnostics were generated from the included observations. Select the button to execute four fresh chains offline (1,200 draws per chain, including 300 burn-in draws).")
    if st.button("Run fresh Bayesian estimation", type="primary"):
        run_mcmc(data)
        st.success(f"Four chains completed. Mean acceptance rate: {st.session_state.acceptance:.2f}")
    current = posterior()
    summary = posterior_summary(current)
    diagnostics = st.session_state.get("sampling_diagnostics")
    if diagnostics is None:
        diagnostics = saved_diagnostics()
    display_summary = summary.copy()
    display_summary["parameter"] = display_summary["parameter"].map(PARAMETER_LABELS)
    st.dataframe(
        display_summary.style.format(
            {
                "posterior_mean": "{:.3g}",
                "median": "{:.3g}",
                "credible_interval_2_5": "{:.3g}",
                "credible_interval_97_5": "{:.3g}",
            }
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "parameter": st.column_config.TextColumn("Parameter"),
            "posterior_mean": st.column_config.NumberColumn("Posterior mean", format="%.3g"),
            "median": st.column_config.NumberColumn("Median", format="%.3g"),
            "credible_interval_2_5": st.column_config.NumberColumn("95% interval: lower", format="%.3g"),
            "credible_interval_97_5": st.column_config.NumberColumn("95% interval: upper", format="%.3g"),
        },
    )
    first, second, third = st.columns(3)
    first.metric("Retained posterior draws", f"{len(current):,}")
    second.metric("Mean chain acceptance", f"{float(diagnostics['mean_acceptance_rate'].iloc[0]):.0%}")
    second.caption("Acceptance is a sampler diagnostic, not model accuracy.")
    third.metric("Estimated parameters", len(current.columns))

    st.subheader("Sampling diagnostics")
    diagnostic_chart = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["Effective sample size", "Split R-hat"],
        horizontal_spacing=0.2,
    )
    diagnostic_labels = diagnostics["parameter"].map(PARAMETER_LABELS)
    diagnostic_chart.add_trace(
        go.Bar(
            x=diagnostics["effective_sample_size"],
            y=diagnostic_labels,
            orientation="h",
            marker_color=COLORS["teal"],
            text=diagnostics["effective_sample_size"].map(lambda value: f"{value:.0f}"),
            textposition="outside",
            hovertemplate="%{y}<br>Estimated ESS: %{x:.1f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    diagnostic_chart.add_trace(
        go.Bar(
            x=diagnostics["split_rhat"],
            y=diagnostic_labels,
            orientation="h",
            marker_color=COLORS["blue"],
            text=diagnostics["split_rhat"].map(lambda value: f"{value:.3f}"),
            textposition="outside",
            hovertemplate="%{y}<br>Split R-hat: %{x:.3f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    diagnostic_chart.update_xaxes(title_text="Estimated draws", row=1, col=1)
    diagnostic_chart.update_xaxes(title_text="Split R-hat", row=1, col=2)
    diagnostic_chart.update_yaxes(autorange="reversed", row=1, col=1)
    diagnostic_chart.update_yaxes(autorange="reversed", row=1, col=2, showticklabels=False)
    st.plotly_chart(style_figure(diagnostic_chart, height=410), width="stretch")
    st.dataframe(
        diagnostics.style.format(
            {"effective_sample_size": "{:.1f}", "split_rhat": "{:.3f}", "mean_acceptance_rate": "{:.3f}"},
            na_rep="n/a",
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "parameter": st.column_config.TextColumn(
                "Parameter",
                help="Values are conditional on this simplified model and the included observations.",
            ),
            "effective_sample_size": st.column_config.NumberColumn("Estimated ESS", format="%.1f"),
            "split_rhat": st.column_config.NumberColumn("Split R-hat", format="%.3f"),
            "mean_acceptance_rate": st.column_config.NumberColumn("Mean acceptance", format="%.1%"),
        },
    )
    st.caption("ESS estimates independent-draw equivalents after autocorrelation. Split R-hat compares chain distributions. These diagnostics do not prove convergence; interpret them cautiously given only 11 observed dates.")
    selected = st.selectbox("Posterior parameter", list(current.columns))
    parameter_summary = summary.loc[summary["parameter"] == selected].iloc[0]
    parameter_label = PARAMETER_LABELS[selected]
    figure = px.histogram(
        current,
        x=selected,
        nbins=45,
        histnorm="probability density",
        labels={selected: PARAMETER_UNITS[selected], "count": "Posterior density"},
        title=f"Posterior distribution: {parameter_label}",
    )
    figure.update_traces(marker_color=COLORS["teal"], opacity=0.78)
    figure.add_vrect(
        x0=parameter_summary["credible_interval_2_5"],
        x1=parameter_summary["credible_interval_97_5"],
        fillcolor=COLORS["blue"],
        opacity=0.12,
        line_width=0,
        annotation_text="95% credible interval",
        annotation_position="top left",
    )
    figure.add_vline(
        x=parameter_summary["median"],
        line_color=COLORS["coral"],
        line_dash="dash",
        line_width=2,
        annotation_text="Median",
        annotation_position="top right",
    )
    st.plotly_chart(style_figure(figure, height=450), width="stretch")
    st.caption("Shaded area marks the equal-tail 95% posterior credible interval; the dashed line is the posterior median. Priors are truncated log-normal and the likelihood uses log-normal observation error.")

elif section == "Dataset Upload":
    st.subheader("Upload observation CSV")
    st.write("Upload a CSV with `date`, `sst_c`, and `chlorophyll_mg_m3` columns. Uploaded rows stay in this Streamlit session and are kept separate from the bundled observations.")
    st.download_button(
        "Download CSV template",
        data="date,sst_c,chlorophyll_mg_m3\n",
        file_name="oceansense_observations_template.csv",
        mime="text/csv",
    )
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"], key="observation_csv")
    if uploaded_file is None:
        uploaded_observations = st.session_state.get("uploaded_observations")
        if uploaded_observations is None:
            st.info("Choose a CSV file to validate and preview its observations.")
        else:
            filename = st.session_state.get("uploaded_filename", "uploaded CSV")
            st.info(
                f"{filename} remains available for this session: "
                f"{len(uploaded_observations)} valid observation records."
            )
            st.dataframe(uploaded_observations.head(10), width="stretch", hide_index=True)
    else:
        try:
            uploaded_observations = validate_uploaded_csv(uploaded_file.getvalue())
        except ValueError as error:
            st.session_state.pop("uploaded_observations", None)
            st.session_state.pop("uploaded_filename", None)
            st.session_state.pop("uploaded_dataset_id", None)
            st.error(str(error))
        else:
            st.session_state.uploaded_observations = uploaded_observations
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.uploaded_dataset_id = hashlib.sha256(
                uploaded_file.getvalue()
            ).hexdigest()
            st.success(f"{len(uploaded_observations)} valid observation records.")
            st.dataframe(uploaded_observations.head(10), width="stretch", hide_index=True)

elif section == "Interactive Prediction":
    st.subheader("Date-specific posterior predictive estimate")
    dataset_choice = st.selectbox("Dataset", ["Bundled Dataset", "Uploaded Dataset"])
    if dataset_choice == "Bundled Dataset":
        prediction_data = data
        dataset_id = "bundled"
    else:
        prediction_data = st.session_state.get("uploaded_observations")
        if prediction_data is None:
            st.info("Upload and validate a CSV in the Dataset Upload section first.")
            st.stop()
        dataset_id = st.session_state.get("uploaded_dataset_id", "uploaded")

    prediction_data = prediction_data.sort_values("date").reset_index(drop=True)
    available_dates = prediction_data["date"].dt.strftime("%Y-%m-%d").tolist()
    selected_date_label = st.selectbox("Observation date", available_dates)
    selected_date = pd.Timestamp(selected_date_label)
    selected_observation = prediction_data.loc[
        prediction_data["date"] == selected_date
    ].iloc[0]

    first, second = st.columns(2)
    first.metric("Observed SST", f"{selected_observation['sst_c']:.2f} °C")
    second.metric(
        "Observed Chlorophyll-a",
        f"{selected_observation['chlorophyll_mg_m3']:.3f} mg/m³",
    )

    year_count = int((prediction_data["date"].dt.year == selected_date.year).sum())
    if year_count < 2:
        st.warning(
            "A prediction needs at least two SST observations in the selected "
            "calendar year to provide interpolated model forcing."
        )

    prediction_key = (dataset_id, selected_date.isoformat())
    if st.button("Run Prediction", type="primary", disabled=year_count < 2):
        prediction = posterior_prediction_for_date(
            posterior(),
            prediction_data,
            selected_date,
        )
        st.session_state.interactive_prediction = {
            "key": prediction_key,
            **prediction,
        }

    saved_prediction = st.session_state.get("interactive_prediction")
    if saved_prediction is not None and saved_prediction["key"] == prediction_key:
        st.metric(
            "Predicted Chlorophyll-a",
            f"{saved_prediction['median']:.3f} mg/m³",
        )
        st.caption(
            "95% parameter interval: "
            f"{saved_prediction['lower_95']:.3f}–"
            f"{saved_prediction['upper_95']:.3f} mg/m³."
        )
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=["Observed", "Model prediction"],
                y=[
                    selected_observation["chlorophyll_mg_m3"],
                    saved_prediction["median"],
                ],
                mode="markers",
                marker={"color": [COLORS["coral"], COLORS["teal"]], "size": 13},
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": [
                        0,
                        saved_prediction["upper_95"] - saved_prediction["median"],
                    ],
                    "arrayminus": [
                        0,
                        saved_prediction["median"] - saved_prediction["lower_95"],
                    ],
                    "visible": True,
                    "color": COLORS["teal"],
                    "thickness": 2,
                    "width": 6,
                },
                hovertemplate="%{x}<br>Chlorophyll-a: %{y:.3f} mg/m³<extra></extra>",
            )
        )
        figure.update_layout(
            title=f"Observed and predicted chlorophyll-a on {selected_date:%Y-%m-%d}",
            xaxis_title="",
            yaxis_title="Chlorophyll-a (mg/m³)",
        )
        st.plotly_chart(style_figure(figure, height=380), width="stretch")

    st.caption(
        "This is a posterior predictive estimate for an observed date, not a future "
        "forecast. The existing posterior was calibrated on bundled observations. "
        "Uploaded chlorophyll values are only shown for comparison; they are not used "
        "to fit or update the model. Uploaded SST values provide model forcing. "
        "The 95% interval reflects parameter uncertainty only, not measurement or "
        "model-structure uncertainty."
    )

elif section == "Prediction and Uncertainty Analysis":
    st.subheader("Posterior predictive uncertainty")
    current = predictive(data)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=current.day,
            y=current.upper_95,
            mode="lines",
            line={"width": 0},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=current.day,
            y=current.lower_95,
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(22,140,134,0.18)",
            name="95% parameter interval",
            hovertemplate="Day %{x}<br>Lower interval: %{y:.3f} mg/m³<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=current.day,
            y=current.median_chlorophyll_mg_m3,
            mode="lines",
            line={"color": COLORS["teal"], "width": 2.8},
            name="Posterior median",
            hovertemplate="Day %{x}<br>Median: %{y:.3f} mg/m³<extra></extra>",
        )
    )
    reference = pd.Timestamp(data.date.min().year, 1, 1)
    observed_days = (data.date - reference).dt.days
    figure.add_trace(
        go.Scatter(
            x=observed_days,
            y=data.chlorophyll_mg_m3,
            mode="markers",
            marker={"color": COLORS["coral"], "size": 10, "line": {"color": "#ffffff", "width": 1.5}},
            customdata=data[["date", "chlorophyll_source_file"]].astype(str),
            name="Satellite observations",
            hovertemplate="Observed %{customdata[0]|%Y-%m-%d}<br>Chlorophyll-a: %{y:.3f} mg/m³<br>Source: %{customdata[1]}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Observed chlorophyll-a and model-based posterior predictions",
        xaxis_title="Day of 2003",
        yaxis_title="Chlorophyll-a (mg/m³)",
    )
    st.plotly_chart(style_figure(figure, height=490), width="stretch")
    st.caption("Red points are the satellite observations; the teal line and shaded band are the posterior median and 95% parameter interval from the saved or freshly sampled posterior.")
    st.caption("The interval propagates parameter uncertainty only. It excludes satellite retrieval error, model structural error, and uncertainty in unobserved MLD/PAR.")

else:
    st.subheader("Results and limitations")
    st.dataframe(posterior_summary(posterior()).round(4), width="stretch", hide_index=True)
    st.subheader("Posterior sampling diagnostics")
    results_diagnostics = st.session_state.get("sampling_diagnostics")
    if results_diagnostics is None:
        results_diagnostics = saved_diagnostics()
    st.dataframe(
        results_diagnostics.style.format(
            {"effective_sample_size": "{:.1f}", "split_rhat": "{:.3f}", "mean_acceptance_rate": "{:.3f}"},
            na_rep="n/a",
        ),
        width="stretch",
        hide_index=True,
    )
    st.markdown("""
    **What the evidence supports**

    The application loads real bundled chlorophyll and SST data, executes a temperature-driven NPZD model, and samples a Bayesian posterior conditional on the selected 2003 observations. The bundled run used four chains; its estimated effective sample sizes are modest and split R-hat is not proof of convergence.

    **Limits of interpretation**

    The selected public chlorophyll source is a cloud-screened daily satellite product, so sample dates have unequal pixel counts and September 2003 is absent in the bundled subset. Copernicus monthly chlorophyll data require registered access in this environment, so this project uses the documented, credential-free JRC alternative and does not claim it is the Copernicus OMI record. MLD and PAR could not be bundled from a credential-free compatible product; they are not shown as observations. The NPZD model is intentionally reduced and the short time series gives wide parameter intervals.
    """)
