"""
plot_timeseries.py — Stage UI-3
==========================================================
Generates time-series diagnostic plots:
  • Temperature zones (equatorial / mid-lat / polar)
  • Max absolute streamfunction Ψ vs time
  • Altitude–temperature profile (if available)
  • Simulation energy log (if available)

Each function returns a list of file paths that were created.
Returns an empty list (with a printed warning) if the source
CSV is absent or cannot be parsed.
==========================================================
"""

import os
import sys

# Allow importing sibling modules when run directly
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from typing import List

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import plotly.graph_objects as go

from data_loader import (
    read_csv_safe, normalize_columns, get_column,
    find_latest_file, extract_step_from_filename,
    set_mpl_style, PALETTE,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _scatter_style(n: int, color: str, width: int = 2) -> dict:
    """
    Return a complete Plotly Scatter kwargs dict (mode + line + marker)
    so callers NEVER pass 'line=' or 'marker=' separately — doing so
    would cause 'multiple values for keyword argument' errors.

    • n == 1  →  markers only (single data point)
    • n > 1   →  lines (with a small dot at each point if n <= 5)
    """
    if n <= 1:
        return {
            "mode":   "markers",
            "marker": dict(size=12, color=color, symbol="circle"),
            "line":   dict(color=color, width=width),   # ignored but safe
        }
    if n <= 5:
        return {
            "mode":   "lines+markers",
            "line":   dict(color=color, width=width),
            "marker": dict(size=7, color=color),
        }
    return {
        "mode": "lines",
        "line": dict(color=color, width=width),
        "marker": dict(size=0),   # hidden; keeps Plotly happy
    }


def _mpl_plot_series(ax, x, y, **kwargs):
    """Plot a line + marker for small datasets, line only for larger ones."""
    if len(x) <= 3:
        ax.plot(x, y, marker="o", markersize=6, **kwargs)
    else:
        ax.plot(x, y, **kwargs)


# ------------------------------------------------------------------
# Temperature zones time-series
# ------------------------------------------------------------------

def plot_temperature_zones(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """
    Read temperature_zones.csv and generate:
      png/temperature_zones_timeseries.png
      report_figures/temperature_zones_timeseries_300dpi.png
      html/temperature_zones_timeseries.html
    """
    generated: List[str] = []
    csv_path = os.path.join(input_dir, "temperature_zones.csv")
    df = read_csv_safe(csv_path)
    if df is None:
        print("  [WARN] temperature_zones.csv not found — skipping temperature zones plot.")
        return generated

    df = normalize_columns(df)
    step_col = get_column(df, "step")
    eq_col   = get_column(df, "temp_equatorial")
    mid_col  = get_column(df, "temp_midlatitude")
    pol_col  = get_column(df, "temp_polar")

    if step_col is None:
        print("  [WARN] 'step' column not found in temperature_zones.csv — skipping.")
        return generated

    x = df[step_col].values
    has_any = any(c is not None for c in [eq_col, mid_col, pol_col])
    if not has_any:
        print("  [WARN] No temperature zone columns found in temperature_zones.csv — skipping.")
        return generated

    # ---- Matplotlib PNG ------------------------------------------------
    set_mpl_style()
    fig, ax = plt.subplots(figsize=(11, 5))

    if eq_col:
        _mpl_plot_series(ax, x, df[eq_col].values,
                         label="Equatorial (0–30°)", color=PALETTE["equatorial"], lw=2.0)
    if mid_col:
        _mpl_plot_series(ax, x, df[mid_col].values,
                         label="Mid-latitude (30–60°)", color=PALETTE["midlatitude"], lw=2.0)
    if pol_col:
        _mpl_plot_series(ax, x, df[pol_col].values,
                         label="Polar (60–90°)", color=PALETTE["polar"], lw=2.0)

    ax.set_xlabel("Simulation step", fontsize=11)
    ax.set_ylabel("Mean kinetic temperature (model units)", fontsize=11)
    ax.set_title("Mean kinetic temperature by latitude zone\n"
                 "(simulation diagnostic — not a real temperature calibration)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(loc="upper right")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    plt.tight_layout()

    png_path = os.path.join(out_dir, "png",            "temperature_zones_timeseries.png")
    rpt_path = os.path.join(out_dir, "report_figures", "temperature_zones_timeseries_300dpi.png")
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    fig.savefig(rpt_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    generated += [png_path, rpt_path]
    if verbose:
        print(f"  [OK] {os.path.relpath(png_path)}")
        print(f"  [OK] {os.path.relpath(rpt_path)}")

    # ---- Plotly HTML ---------------------------------------------------
    pfig = go.Figure()
    n = len(x)
    if eq_col:
        pfig.add_trace(go.Scatter(x=x, y=df[eq_col].values,
                                  name="Equatorial (0–30°)",
                                  **_scatter_style(n, PALETTE["equatorial"])))
    if mid_col:
        pfig.add_trace(go.Scatter(x=x, y=df[mid_col].values,
                                  name="Mid-latitude (30–60°)",
                                  **_scatter_style(n, PALETTE["midlatitude"])))
    if pol_col:
        pfig.add_trace(go.Scatter(x=x, y=df[pol_col].values,
                                  name="Polar (60–90°)",
                                  **_scatter_style(n, PALETTE["polar"])))

    pfig.update_layout(
        title=dict(
            text="Mean kinetic temperature by latitude zone<br>"
                 "<sup>Simulation diagnostic — not a real temperature calibration</sup>",
            font=dict(size=16),
        ),
        xaxis_title="Simulation step",
        yaxis_title="Mean kinetic temperature (model units)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=60, r=40, t=80, b=80),
    )
    html_path = os.path.join(out_dir, "html", "temperature_zones_timeseries.html")
    pfig.write_html(html_path, include_plotlyjs=True)
    generated.append(html_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(html_path)}")

    return generated


# ------------------------------------------------------------------
# Max absolute Ψ vs time
# ------------------------------------------------------------------

def plot_max_abs_psi(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """
    Read streamfunction_summary.csv and generate max|Ψ| time-series.
    Falls back to computing max_abs_psi from min_psi / max_psi if needed.
    """
    generated: List[str] = []
    csv_path = os.path.join(input_dir, "streamfunction_summary.csv")
    df = read_csv_safe(csv_path)
    if df is None:
        print("  [WARN] streamfunction_summary.csv not found — skipping max|Ψ| plot.")
        return generated

    df = normalize_columns(df)
    step_col = get_column(df, "step")
    if step_col is None:
        print("  [WARN] 'step' column missing in streamfunction_summary.csv — skipping.")
        return generated

    psi_col = get_column(df, "max_abs_psi")
    if psi_col is None:
        min_c = get_column(df, "min_psi")
        max_c = get_column(df, "max_psi")
        if min_c and max_c:
            df["_max_abs_psi"] = np.maximum(df[min_c].abs(), df[max_c].abs())
            psi_col = "_max_abs_psi"
        else:
            print("  [WARN] Cannot derive max_abs_psi from streamfunction_summary.csv — skipping.")
            return generated

    x = df[step_col].values
    y = df[psi_col].values

    # ---- Matplotlib PNG ------------------------------------------------
    set_mpl_style()
    fig, ax = plt.subplots(figsize=(11, 5))
    _mpl_plot_series(ax, x, y, color=PALETTE["psi"], lw=2.0, label="max |Ψ|")
    ax.set_xlabel("Simulation step", fontsize=11)
    ax.set_ylabel("max |Ψ| (model units)", fontsize=11)
    ax.set_title(
        "Maximum absolute streamfunction amplitude vs time\n"
        "(streamfunction diagnostic — candidate meridional circulation structure)",
        fontsize=12, fontweight="bold", pad=10,
    )
    ax.legend()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    plt.tight_layout()

    png_path = os.path.join(out_dir, "png",            "max_abs_psi_vs_time.png")
    rpt_path = os.path.join(out_dir, "report_figures", "max_abs_psi_vs_time_300dpi.png")
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    fig.savefig(rpt_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    generated += [png_path, rpt_path]
    if verbose:
        print(f"  [OK] {os.path.relpath(png_path)}")

    # ---- Plotly HTML ---------------------------------------------------
    pfig = go.Figure()
    pfig.add_trace(go.Scatter(x=x, y=y, name="max |Ψ|",
                              **_scatter_style(len(x), PALETTE["psi"], width=2)))
    pfig.update_layout(
        title=dict(
            text="Maximum absolute streamfunction amplitude vs time<br>"
                 "<sup>Streamfunction diagnostic — candidate meridional circulation structure</sup>",
            font=dict(size=16),
        ),
        xaxis_title="Simulation step",
        yaxis_title="max |Ψ| (model units)",
        template="plotly_white",
        margin=dict(l=60, r=40, t=80, b=60),
    )
    html_path = os.path.join(out_dir, "html", "max_abs_psi_vs_time.html")
    pfig.write_html(html_path, include_plotlyjs=True)
    generated.append(html_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(html_path)}")

    return generated


# ------------------------------------------------------------------
# Altitude–temperature profile
# ------------------------------------------------------------------

def plot_altitude_temperature(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """Read altitude_temperature_profile.csv and plot T vs altitude.

    Accepts columns: altitude_center / altitude / alt / h / height
    and mean_temperature / temperature / T_p / temp / T / mean_T.
    Also generates an interactive Plotly HTML.
    """
    generated: List[str] = []
    csv_path = os.path.join(input_dir, "altitude_temperature_profile.csv")
    df = read_csv_safe(csv_path)
    if df is None:
        if verbose:
            print("  [INFO] altitude_temperature_profile.csv not found — skipping.")
        return generated

    df = normalize_columns(df)

    if verbose:
        print(f"  [ALT-T] CSV columns: {list(df.columns)}")

    alt_col  = get_column(df, "altitude")
    temp_col = get_column(df, "T_p")

    if alt_col is None or temp_col is None:
        missing = []
        if alt_col is None:  missing.append("altitude (tried altitude_center, alt, h, height)")
        if temp_col is None: missing.append("temperature (tried mean_temperature, T_p, temp)")
        msg = (f"altitude_temperature_profile.csv missing columns: "
               f"{', '.join(missing)}. Found: {list(df.columns)}")
        print(f"  [WARN] {msg}")
        # Write to missing outputs report
        miss_path = os.path.join(out_dir, "summary", "missing_required_outputs.md")
        try:
            with open(miss_path, "a", encoding="utf-8") as fh:
                fh.write(f"\n## altitude_temperature_profile\n{msg}\n")
        except Exception:
            pass
        return generated

    alt_vals  = df[alt_col].values.astype(float)
    temp_vals = df[temp_col].values.astype(float)

    if verbose:
        print(f"  [ALT-T] Using alt='{alt_col}', temp='{temp_col}', {len(alt_vals)} rows")
        print(f"  [ALT-T] alt range: {alt_vals.min():.2f} - {alt_vals.max():.2f}")
        print(f"  [ALT-T] temp range: {temp_vals.min():.4g} - {temp_vals.max():.4g}")

    # ---- Matplotlib static PNG ----
    set_mpl_style()
    fig, ax = plt.subplots(figsize=(6, 9))
    ax.plot(temp_vals, alt_vals, color=PALETTE["total_q"], lw=2.2, marker="o",
            markersize=5, markerfacecolor="white", markeredgewidth=1.5)
    ax.set_xlabel("Temperature (model units)", fontsize=11)
    ax.set_ylabel("Altitude (model units)", fontsize=11)
    ax.set_title("Altitude-temperature profile\n(simulation diagnostic)", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.35)
    plt.tight_layout()

    png_path = os.path.join(out_dir, "png",            "altitude_temperature_profile.png")
    rpt_path = os.path.join(out_dir, "report_figures", "altitude_temperature_profile_300dpi.png")
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    fig.savefig(rpt_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    generated += [png_path, rpt_path]
    if verbose:
        print(f"  [OK] {os.path.relpath(png_path)}")

    # ---- Plotly interactive HTML ----
    try:
        pfig = go.Figure()
        pfig.add_trace(go.Scatter(
            x=temp_vals,
            y=alt_vals,
            mode="lines+markers",
            line=dict(color="#2563eb", width=2),
            marker=dict(size=7, color="#2563eb",
                        line=dict(color="white", width=1)),
            name="Mean T",
            hovertemplate="Temp: %{x:.4f}<br>Altitude: %{y:.2f}<extra></extra>",
        ))
        pfig.update_layout(
            title=dict(text="Altitude-temperature profile (simulation diagnostic)",
                       font=dict(size=14, color="#1a2540")),
            xaxis=dict(title="Temperature (model units)", gridcolor="#e2e8f0"),
            yaxis=dict(title="Altitude (model units)", gridcolor="#e2e8f0"),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#1a2540"),
            height=580,
        )
        html_path = os.path.join(out_dir, "html", "altitude_temperature_profile.html")
        pfig.write_html(html_path, include_plotlyjs=True)
        generated.append(html_path)
        if verbose:
            print(f"  [OK] {os.path.relpath(html_path)}")
    except Exception as exc:
        print(f"  [WARN] altitude-temperature Plotly HTML failed: {exc}")

    return generated


# ------------------------------------------------------------------
# Simulation energy log
# ------------------------------------------------------------------

def plot_simulation_energy(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """
    Read simulation_log.csv and plot kinetic / potential / total energy.
    Not a required output, but useful for Stage 1/2 diagnostics.
    """
    generated: List[str] = []
    csv_path = os.path.join(input_dir, "simulation_log.csv")
    df = read_csv_safe(csv_path)
    if df is None:
        if verbose:
            print("  [WARN] simulation_log.csv not found — skipping energy plot.")
        return generated

    df = normalize_columns(df)
    step_col  = get_column(df, "step")
    ekin_col  = get_column(df, "e_kin")
    egrav_col = get_column(df, "e_grav")
    etot_col  = get_column(df, "e_total")

    if step_col is None or not any([ekin_col, egrav_col, etot_col]):
        if verbose:
            print("  [WARN] Energy columns not found in simulation_log.csv — skipping.")
        return generated

    x = df[step_col].values

    set_mpl_style()
    fig, ax = plt.subplots(figsize=(11, 5))
    if ekin_col:
        _mpl_plot_series(ax, x, df[ekin_col].values, label="Kinetic energy",
                         color=PALETTE["equatorial"], lw=2.0)
    if egrav_col:
        _mpl_plot_series(ax, x, df[egrav_col].values, label="Potential energy",
                         color=PALETTE["polar"], lw=2.0)
    if etot_col:
        _mpl_plot_series(ax, x, df[etot_col].values, label="Total energy",
                         color=PALETTE["navy"], lw=2.0, ls="--")

    ax.set_xlabel("Simulation step", fontsize=11)
    ax.set_ylabel("Energy (model units)", fontsize=11)
    ax.set_title("Simulation energy components (diagnostic)", fontsize=12, fontweight="bold")
    ax.legend()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    plt.tight_layout()

    png_path = os.path.join(out_dir, "png",            "simulation_energy.png")
    rpt_path = os.path.join(out_dir, "report_figures", "simulation_energy_300dpi.png")
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    fig.savefig(rpt_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    generated += [png_path, rpt_path]
    if verbose:
        print(f"  [OK] {os.path.relpath(png_path)}")
    return generated
