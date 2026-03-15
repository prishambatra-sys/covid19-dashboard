"""
COVID-19 Dashboard — Capstone Project
Data Source: Johns Hopkins CSSE COVID-19 Time Series
https://github.com/CSSEGISandData/COVID-19
"""
 
import io
import pandas as pd
import requests
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
from plotly.subplots import make_subplots
 
# ── Data URLs ────────────────────────────────────────────────────────────────
BASE = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/"
URLS = {
    "confirmed": BASE + "time_series_covid19_confirmed_global.csv",
    "deaths":    BASE + "time_series_covid19_deaths_global.csv",
    "recovered": BASE + "time_series_covid19_recovered_global.csv",
}
 
# ── Data Loading & Processing ────────────────────────────────────────────────
def load_series(url: str) -> pd.DataFrame:
    """Fetch a CSSE time-series CSV and return a country-aggregated long-form DataFrame."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df = df.drop(columns=["Province/State", "Lat", "Long"], errors="ignore")
    df = df.groupby("Country/Region", as_index=False).sum()
    df = df.melt(id_vars="Country/Region", var_name="date", value_name="cumulative")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["Country/Region", "date"])
    # Compute daily new values (difference); clip negatives (data corrections) to 0
    df["daily"] = df.groupby("Country/Region")["cumulative"].diff().clip(lower=0)
    df["daily"] = df["daily"].fillna(0).astype(int)
    # 7-day rolling average of daily
    df["rolling7"] = (
        df.groupby("Country/Region")["daily"]
        .transform(lambda x: x.rolling(7, min_periods=1).mean())
    )
    return df
 
print("Loading COVID-19 data from CSSE…")
try:
    confirmed_df  = load_series(URLS["confirmed"])
    deaths_df     = load_series(URLS["deaths"])
    try:
        recovered_df = load_series(URLS["recovered"])
        has_recovered = True
    except Exception:
        recovered_df  = None
        has_recovered = False
 
    ALL_COUNTRIES = sorted(confirmed_df["Country/Region"].unique().tolist())
    DATA_LOADED   = True
    LOAD_ERROR    = ""
    print(f"✓ Loaded {len(ALL_COUNTRIES)} countries.")
except Exception as e:
    DATA_LOADED  = False
    LOAD_ERROR   = str(e)
    ALL_COUNTRIES = []
    print(f"✗ Load failed: {e}")
 
# ── Colour palette ────────────────────────────────────────────────────────────
PALETTE = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373",
    "#CE93D8", "#4DD0E1", "#AED581", "#FFD54F",
    "#FF8A65", "#90CAF9",
]
 
# ── Dash App ──────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="COVID-19 Global Dashboard")
server = app.server   # expose WSGI for deployment
 
DEFAULT_COUNTRIES = ["US", "United Kingdom", "India", "Brazil", "France"]
 
app.layout = html.Div(
    style={"fontFamily": "'Segoe UI', Helvetica, Arial, sans-serif",
           "background": "#0d1117", "minHeight": "100vh", "color": "#e6edf3"},
    children=[
 
        # ── Header ──────────────────────────────────────────────────────────
        html.Div(style={
            "background": "linear-gradient(135deg, #161b22 0%, #0d1117 100%)",
            "borderBottom": "1px solid #30363d",
            "padding": "24px 40px 20px",
        }, children=[
            html.H1("🌐 COVID-19 Global Dashboard",
                    style={"margin": 0, "fontSize": "28px", "fontWeight": "700",
                           "letterSpacing": "-0.5px", "color": "#58a6ff"}),
            html.P("Data: Johns Hopkins CSSE — updated daily via GitHub",
                   style={"margin": "4px 0 0", "fontSize": "13px", "color": "#8b949e"}),
        ]),
 
        # ── Controls ─────────────────────────────────────────────────────────
        html.Div(style={
            "display": "flex", "flexWrap": "wrap", "gap": "20px",
            "padding": "20px 40px", "background": "#161b22",
            "borderBottom": "1px solid #30363d", "alignItems": "flex-end",
        }, children=[
 
            # Country selector
            html.Div(style={"flex": "1", "minWidth": "260px"}, children=[
                html.Label("Add Countries", style={"fontSize": "12px", "color": "#8b949e",
                                                    "textTransform": "uppercase",
                                                    "letterSpacing": "0.8px",
                                                    "marginBottom": "6px", "display": "block"}),
                dcc.Dropdown(
                    id="country-dropdown",
                    options=[{"label": c, "value": c} for c in ALL_COUNTRIES],
                    multi=True,
                    value=DEFAULT_COUNTRIES,
                    placeholder="Select countries…",
                    style={"background": "#0d1117", "color": "#e6edf3"},
                    className="dark-dropdown",
                ),
            ]),
 
            # Metric selector
            html.Div(style={"minWidth": "160px"}, children=[
                html.Label("Metric", style={"fontSize": "12px", "color": "#8b949e",
                                             "textTransform": "uppercase",
                                             "letterSpacing": "0.8px",
                                             "marginBottom": "6px", "display": "block"}),
                dcc.Dropdown(
                    id="metric-dropdown",
                    options=[
                        {"label": "Confirmed Cases", "value": "confirmed"},
                        {"label": "Deaths",           "value": "deaths"},
                        {"label": "Recovered",        "value": "recovered"},
                    ],
                    value="confirmed",
                    clearable=False,
                    style={"background": "#0d1117"},
                ),
            ]),
 
            # View mode
            html.Div(style={"minWidth": "220px"}, children=[
                html.Label("View Mode", style={"fontSize": "12px", "color": "#8b949e",
                                                "textTransform": "uppercase",
                                                "letterSpacing": "0.8px",
                                                "marginBottom": "6px", "display": "block"}),
                dcc.RadioItems(
                    id="view-mode",
                    options=[
                        {"label": "  Cumulative", "value": "cumulative"},
                        {"label": "  Daily New",  "value": "daily"},
                        {"label": "  7-Day Avg",  "value": "rolling7"},
                    ],
                    value="cumulative",
                    inline=True,
                    style={"fontSize": "14px", "color": "#c9d1d9", "gap": "12px"},
                    labelStyle={"marginRight": "18px", "color": "#c9d1d9"},
                ),
            ]),
 
            # Log scale toggle
            html.Div(style={"minWidth": "120px"}, children=[
                html.Label("Scale", style={"fontSize": "12px", "color": "#c9d1d9",
                                            "textTransform": "uppercase",
                                            "letterSpacing": "0.8px",
                                            "marginBottom": "6px", "display": "block"}),
                dcc.Checklist(
                    id="log-scale",
                    options=[{"label": "  Log scale", "value": "log"}],
                    value=[],
                    style={"fontSize": "14px", "color": "#c9d1d9"},
                ),
            ]),
        ]),
 
        # ── Main chart ───────────────────────────────────────────────────────
        html.Div(style={"padding": "24px 40px 0"}, children=[
            dcc.Loading(
                type="circle",
                color="#58a6ff",
                children=[dcc.Graph(id="main-chart", style={"height": "460px"},
                                    config={"displayModeBar": True,
                                            "modeBarButtonsToRemove": ["lasso2d", "select2d"]})],
            ),
        ]),
 
        # ── Summary cards ────────────────────────────────────────────────────
        html.Div(id="summary-cards",
                 style={"display": "flex", "flexWrap": "wrap", "gap": "12px",
                        "padding": "20px 40px"}),
 
        # ── Date range note ──────────────────────────────────────────────────
        html.Div(id="date-note",
                 style={"padding": "0 40px 8px", "fontSize": "12px", "color": "#8b949e"}),
 
        # ── Footer ───────────────────────────────────────────────────────────
        html.Div(style={
            "borderTop": "1px solid #30363d",
            "padding": "16px 40px",
            "fontSize": "12px",
            "color": "#8b949e",
            "marginTop": "12px",
        }, children=[
            "Data source: ",
            html.A("Johns Hopkins CSSE COVID-19 Repository",
                   href="https://github.com/CSSEGISandData/COVID-19",
                   target="_blank",
                   style={"color": "#58a6ff"}),
            " | Dashboard built with Dash & Plotly",
        ]),
 
        # Error banner
        html.Div(
            f"⚠️ Data load error: {LOAD_ERROR}" if not DATA_LOADED else "",
            id="error-banner",
            style={
                "display": "block" if not DATA_LOADED else "none",
                "background": "#5a1d1d", "color": "#ff7b7b",
                "padding": "12px 40px", "fontSize": "14px",
            },
        ),
    ]
)
 
 
# ── Dropdown dark-mode CSS injection ─────────────────────────────────────────
app.index_string = app.index_string.replace(
    "</head>",
    """<style>
    .dark-dropdown .Select-control { background:#0d1117 !important; border-color:#30363d !important; }
    .Select-menu-outer { background:#161b22 !important; border-color:#30363d !important; }
    .Select-option { background:#161b22 !important; color:#e6edf3 !important; }
    .Select-option:hover, .Select-option.is-focused { background:#1f2937 !important; }
    .Select-value-label { color:#e6edf3 !important; }
    .Select-placeholder { color:#8b949e !important; }
    .Select-input input { color:#e6edf3 !important; }
    </style></head>""",
)
 
 
# ── Callbacks ─────────────────────────────────────────────────────────────────
@app.callback(
    Output("main-chart",    "figure"),
    Output("summary-cards", "children"),
    Output("date-note",     "children"),
    Input("country-dropdown", "value"),
    Input("metric-dropdown",  "value"),
    Input("view-mode",        "value"),
    Input("log-scale",        "value"),
)
def update_dashboard(countries, metric, view_mode, log_scale):
    if not DATA_LOADED:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                          title="Data unavailable")
        return fig, [], ""
 
    countries = countries or []
 
    # Pick dataframe
    if metric == "confirmed":
        df = confirmed_df
        metric_label = "Confirmed Cases"
        metric_color_base = "#58a6ff"
    elif metric == "deaths":
        df = deaths_df
        metric_label = "Deaths"
        metric_color_base = "#f85149"
    else:
        if not has_recovered:
            df = confirmed_df
            metric_label = "Confirmed Cases (recovered N/A)"
            metric_color_base = "#58a6ff"
        else:
            df = recovered_df
            metric_label = "Recovered"
            metric_color_base = "#3fb950"
 
    view_label = {"cumulative": "Cumulative", "daily": "Daily New", "rolling7": "7-Day Rolling Avg"}[view_mode]
    title_text = f"{view_label} {metric_label}"
 
    use_log = "log" in (log_scale or [])
 
    fig = go.Figure()
 
    summary_cards = []
 
    for i, country in enumerate(countries):
        cdata = df[df["Country/Region"] == country].copy()
        if cdata.empty:
            continue
        color = PALETTE[i % len(PALETTE)]
 
        y_col = view_mode
        fig.add_trace(go.Scatter(
            x=cdata["date"],
            y=cdata[y_col],
            mode="lines",
            name=country,
            line=dict(color=color, width=2.5),
            hovertemplate=(
                f"<b>{country}</b><br>"
                "Date: %{x|%b %d, %Y}<br>"
                f"{view_label}: %{{y:,.0f}}<extra></extra>"
            ),
        ))
 
        # Summary card — latest values
        latest = cdata.dropna(subset=["cumulative"]).iloc[-1]
        latest_date = latest["date"].strftime("%b %d, %Y")
        cumul_val   = int(latest["cumulative"])
        daily_val   = int(latest["daily"])
        roll_val    = round(latest["rolling7"], 1)
 
        summary_cards.append(html.Div(style={
            "background": "#161b22",
            "border": f"1px solid {color}40",
            "borderTop": f"3px solid {color}",
            "borderRadius": "8px",
            "padding": "14px 18px",
            "minWidth": "200px",
            "flex": "1",
        }, children=[
            html.Div(country, style={"fontWeight": "700", "fontSize": "15px", "color": color}),
            html.Div(latest_date, style={"fontSize": "11px", "color": "#8b949e", "marginBottom": "8px"}),
            html.Div([
                html.Span("Cumulative", style={"fontSize": "11px", "color": "#8b949e"}),
                html.Div(f"{cumul_val:,}", style={"fontSize": "20px", "fontWeight": "700"}),
            ]),
            html.Div([
                html.Span("Daily New ", style={"fontSize": "11px", "color": "#8b949e"}),
                html.Span(f"{daily_val:,}", style={"fontSize": "13px"}),
                html.Span("  7d Avg ", style={"fontSize": "11px", "color": "#8b949e"}),
                html.Span(f"{roll_val:,.1f}", style={"fontSize": "13px"}),
            ], style={"marginTop": "4px"}),
        ]))
 
    # Layout
    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        font=dict(color="#e6edf3", family="'Segoe UI', sans-serif"),
        title=dict(text=title_text, font=dict(size=18, color="#e6edf3"), x=0.01),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
                    font=dict(size=12)),
        xaxis=dict(
            gridcolor="#21262d", zeroline=False,
            showline=True, linecolor="#30363d",
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            type="log" if use_log else "linear",
            gridcolor="#21262d", zeroline=False,
            showline=True, linecolor="#30363d",
            tickformat=",",
            tickfont=dict(size=11),
        ),
        hovermode="x unified",
        margin=dict(l=60, r=20, t=60, b=50),
    )
 
    if df is not None and not df.empty:
        date_range = (f"Data range: {df['date'].min().strftime('%b %d, %Y')} — "
                      f"{df['date'].max().strftime('%b %d, %Y')}")
    else:
        date_range = ""
 
    return fig, summary_cards, date_range
 
 
# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nStarting COVID-19 Dashboard…  http://127.0.0.1:8050/\n")
    app.run(debug=False, host="0.0.0.0", port=8050)