"""
plot_moisture.py — Stage UI-3
==========================================================
Generates moisture-related diagnostic plots:
  • Water-balance panels (4-panel figure)
  • Evaporation & condensation time-series (combined + separated)
  • Moisture heatmaps (from particle_spherical_step_*.csv)

Writes summary JSON files consumed by manifest_builder and
embedded into window.DASHBOARD_MANIFEST.summaryData.
==========================================================
"""

import os
import sys
import json

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_loader import (
    read_csv_safe, normalize_columns, get_column,
    find_latest_file, downsample_dataframe,
    extract_step_from_filename,
    report_csv_columns, check_required_columns,
    set_mpl_style, PALETTE,
)


def _mpl_plot_series(ax, x, y, **kwargs):
    if len(x) <= 3:
        ax.plot(x, y, marker="o", markersize=5, **kwargs)
    else:
        ax.plot(x, y, **kwargs)


def _x_formatter(ax):
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{int(v):,}")
    )


# ------------------------------------------------------------------
# Water balance panels
# ------------------------------------------------------------------

def plot_water_balance(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """
    Generate water balance panel figures and summary JSON.
    Source: moisture_balance.csv
    """
    generated: List[str] = []
    csv_path = os.path.join(input_dir, "moisture_balance.csv")
    df = read_csv_safe(csv_path)
    if df is None:
        print("  [WARN] moisture_balance.csv not found — skipping water balance.")
        return generated

    df = normalize_columns(df)
    step_col  = get_column(df, "step")
    tq_col    = get_column(df, "total_q")
    etq_col   = get_column(df, "expected_total_q")
    err_col   = get_column(df, "water_balance_error")
    rerr_col  = get_column(df, "water_balance_relative_error")
    cev_col   = get_column(df, "cumulative_evaporation")
    cco_col   = get_column(df, "cumulative_condensation")

    if step_col is None:
        print("  [WARN] 'step' column not found in moisture_balance.csv — skipping.")
        return generated

    x = df[step_col].values
    set_mpl_style()

    # ---- 4-panel Matplotlib figure ------------------------------------
    n_panels = sum([
        bool(tq_col or etq_col),
        bool(cev_col or cco_col),
        bool(err_col),
        bool(rerr_col),
    ]) or 1

    fig = plt.figure(figsize=(13, 3.4 * n_panels))
    gs  = gridspec.GridSpec(n_panels, 1, hspace=0.5)
    p   = 0

    if tq_col or etq_col:
        ax = fig.add_subplot(gs[p]); p += 1
        if tq_col:
            _mpl_plot_series(ax, x, df[tq_col].values,
                             color=PALETTE["total_q"], lw=2.0, label="total_q")
        if etq_col:
            _mpl_plot_series(ax, x, df[etq_col].values,
                             color=PALETTE["expected_q"], lw=2.0, ls="--",
                             label="expected_total_q")
        ax.set_ylabel("Total humidity\n(model units)", fontsize=9)
        ax.set_title("Water balance — total_q vs expected_total_q", fontsize=11)
        ax.legend(loc="upper right"); _x_formatter(ax)

    if cev_col or cco_col:
        ax = fig.add_subplot(gs[p]); p += 1
        if cev_col:
            _mpl_plot_series(ax, x, df[cev_col].values,
                             color=PALETTE["evap"], lw=2.0, label="cumul. evaporation")
        if cco_col:
            _mpl_plot_series(ax, x, df[cco_col].values,
                             color=PALETTE["cond"], lw=2.0, label="cumul. condensation")
        ax.set_ylabel("Cumulative\n(model units)", fontsize=9)
        ax.set_title("Cumulative evaporation and condensation", fontsize=11)
        ax.legend(loc="upper left"); _x_formatter(ax)

    if err_col:
        ax = fig.add_subplot(gs[p]); p += 1
        _mpl_plot_series(ax, x, df[err_col].abs().values,
                         color=PALETTE["error"], lw=1.6)
        ax.set_ylabel("|water balance error|", fontsize=9)
        ax.set_title("Absolute water balance error (diagnostic)", fontsize=11)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        _x_formatter(ax)

    if rerr_col:
        ax = fig.add_subplot(gs[p]); p += 1
        _mpl_plot_series(ax, x, df[rerr_col].abs().values,
                         color=PALETTE["rel_error"], lw=1.6)
        ax.set_ylabel("|relative error|", fontsize=9)
        ax.set_title("Relative water balance error (diagnostic)", fontsize=11)
        ax.axhline(1e-4, ls=":", color=PALETTE["evap"],   lw=1.2,
                   label="PASS ≤ 1e−4")
        ax.axhline(1e-2, ls=":", color=PALETTE["expected_q"], lw=1.2,
                   label="WARNING ≤ 1e−2")
        ax.legend(fontsize=8)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        _x_formatter(ax)

    fig.text(0.5, 0.00, "Simulation step", ha="center", fontsize=11)
    fig.suptitle("Water-balance diagnostic — moisture_balance.csv",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()

    png_path = os.path.join(out_dir, "png",            "water_balance_panels.png")
    rpt_path = os.path.join(out_dir, "report_figures", "water_balance_panels_300dpi.png")
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    fig.savefig(rpt_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    generated += [png_path, rpt_path]
    if verbose:
        print(f"  [OK] {os.path.relpath(png_path)}")

    # ---- Plotly HTML --------------------------------------------------
    rows_h = []
    if tq_col or etq_col:   rows_h.append("total_q vs expected_total_q")
    if cev_col or cco_col:  rows_h.append("Cumulative evaporation & condensation")
    if err_col:             rows_h.append("|water balance error|")
    if rerr_col:            rows_h.append("|relative error|")
    n_rows = len(rows_h) or 1

    pfig = make_subplots(
        rows=n_rows, cols=1,
        subplot_titles=rows_h,
        vertical_spacing=0.09,
    )
    r = 1
    if tq_col:
        pfig.add_trace(go.Scatter(x=x, y=df[tq_col].values, name="total_q",
                                  line=dict(color=PALETTE["total_q"])), row=r, col=1)
    if etq_col:
        pfig.add_trace(go.Scatter(x=x, y=df[etq_col].values, name="expected_total_q",
                                  line=dict(color=PALETTE["expected_q"], dash="dash")),
                       row=r, col=1)
    if tq_col or etq_col: r += 1

    if cev_col:
        pfig.add_trace(go.Scatter(x=x, y=df[cev_col].values, name="cum. evaporation",
                                  line=dict(color=PALETTE["evap"])), row=r, col=1)
    if cco_col:
        pfig.add_trace(go.Scatter(x=x, y=df[cco_col].values, name="cum. condensation",
                                  line=dict(color=PALETTE["cond"])), row=r, col=1)
    if cev_col or cco_col: r += 1

    if err_col:
        pfig.add_trace(go.Scatter(x=x, y=df[err_col].abs().values, name="|error|",
                                  line=dict(color=PALETTE["error"])), row=r, col=1)
        r += 1
    if rerr_col:
        pfig.add_trace(go.Scatter(x=x, y=df[rerr_col].abs().values, name="|rel. error|",
                                  line=dict(color=PALETTE["rel_error"])), row=r, col=1)

    pfig.update_layout(
        height=max(350 * n_rows, 500),
        title="Water-balance diagnostic — moisture_balance.csv",
        template="plotly_white",
        showlegend=True,
    )
    html_path = os.path.join(out_dir, "html", "water_balance_panels.html")
    pfig.write_html(html_path, include_plotlyjs=True)
    generated.append(html_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(html_path)}")

    # ---- Summary JSON -------------------------------------------------
    summary: Dict[str, Any] = {
        "latest_step":                None,
        "latest_total_q":             None,
        "latest_expected_total_q":    None,
        "latest_relative_error":      None,
        "max_abs_relative_error":     None,
        "recommended_status":         "NOT_AVAILABLE",
    }
    try:
        last = df.iloc[-1]
        if step_col:  summary["latest_step"]             = int(last[step_col])
        if tq_col:    summary["latest_total_q"]          = float(last[tq_col])
        if etq_col:   summary["latest_expected_total_q"] = float(last[etq_col])
        if rerr_col:
            rel_series = df[rerr_col].abs()
            max_rel    = float(rel_series.max())
            summary["latest_relative_error"]  = float(last[rerr_col])
            summary["max_abs_relative_error"] = max_rel
            if max_rel <= 1e-4:
                summary["recommended_status"] = "PASS"
            elif max_rel <= 1e-2:
                summary["recommended_status"] = "WARNING"
            else:
                summary["recommended_status"] = "FAIL"
    except Exception as exc:
        print(f"  [WARN] Water balance summary compute failed: {exc}")

    json_path = os.path.join(out_dir, "summary", "water_balance_summary.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    generated.append(json_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(json_path)}"
              f"  status={summary['recommended_status']}")

    return generated


# ------------------------------------------------------------------
# Evaporation & condensation time-series
# ------------------------------------------------------------------

def plot_evap_cond(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """
    Merge evaporation_log.csv + condensation_log.csv and generate:
      • Combined rates + cumulative (4-panel)
      • Rates-only figure
      • Cumulative-only figure
      • Plotly HTML combined view
      • Summary JSON
    """
    generated: List[str] = []

    evap_df = read_csv_safe(os.path.join(input_dir, "evaporation_log.csv"))
    cond_df = read_csv_safe(os.path.join(input_dir, "condensation_log.csv"))

    if evap_df is None and cond_df is None:
        print("  [WARN] Neither evaporation_log.csv nor condensation_log.csv found — skipping.")
        return generated

    # Normalise columns before merge
    if evap_df is not None:
        evap_df = normalize_columns(evap_df)
    if cond_df is not None:
        cond_df = normalize_columns(cond_df)

    # Merge on step
    if evap_df is not None and cond_df is not None:
        se = get_column(evap_df, "step")
        sc = get_column(cond_df, "step")
        if se and sc:
            merged = pd.merge(
                evap_df.rename(columns={se: "step"}),
                cond_df.rename(columns={sc: "step"}),
                on="step", how="outer",
            ).sort_values("step").reset_index(drop=True)
        else:
            merged = evap_df if evap_df is not None else cond_df
    else:
        merged = evap_df if evap_df is not None else cond_df

    merged = normalize_columns(merged)
    x = merged[get_column(merged, "step")].values if get_column(merged, "step") else None
    if x is None:
        print("  [WARN] 'step' column not found after merging evap/cond data — skipping.")
        return generated

    evap_rate_col  = get_column(merged, "evaporation_this_step")
    cond_rate_col  = get_column(merged, "condensation_this_step")
    latent_col     = get_column(merged, "latent_heating_this_step")
    cum_evap_col   = get_column(merged, "cumulative_evaporation")
    cum_cond_col   = get_column(merged, "cumulative_condensation")
    cum_latent_col = get_column(merged, "cumulative_latent_heating")

    set_mpl_style()

    # ---- Rates-only PNG -----------------------------------------------
    has_rates = bool(evap_rate_col or cond_rate_col or latent_col)
    if has_rates:
        n = sum([bool(evap_rate_col), bool(cond_rate_col), bool(latent_col)])
        fig_r, ax_r = plt.subplots(figsize=(11, 4))
        if evap_rate_col:
            _mpl_plot_series(ax_r, x, merged[evap_rate_col].values,
                             color=PALETTE["evap"], lw=1.8, label="evaporation rate")
        if cond_rate_col:
            _mpl_plot_series(ax_r, x, merged[cond_rate_col].values,
                             color=PALETTE["cond"], lw=1.8, label="condensation rate")
        if latent_col:
            _mpl_plot_series(ax_r, x, merged[latent_col].values,
                             color=PALETTE["latent"], lw=1.8, ls="--", label="latent heating rate")
        ax_r.set_xlabel("Simulation step", fontsize=11)
        ax_r.set_ylabel("Rate (model units / step)", fontsize=10)
        ax_r.set_title("Evaporation & condensation rates (per step)", fontsize=12, fontweight="bold")
        ax_r.legend(); _x_formatter(ax_r)
        plt.tight_layout()

        pr_png = os.path.join(out_dir, "png",            "evap_cond_rates_only.png")
        pr_rpt = os.path.join(out_dir, "report_figures", "evap_cond_rates_only_300dpi.png")
        fig_r.savefig(pr_png, dpi=120, bbox_inches="tight")
        fig_r.savefig(pr_rpt, dpi=300, bbox_inches="tight")
        plt.close(fig_r)
        generated += [pr_png, pr_rpt]
        if verbose:
            print(f"  [OK] {os.path.relpath(pr_png)}")

    # ---- Cumulative-only PNG ------------------------------------------
    has_cum = bool(cum_evap_col or cum_cond_col or cum_latent_col)
    if has_cum:
        fig_c, ax_c = plt.subplots(figsize=(11, 4))
        if cum_evap_col:
            _mpl_plot_series(ax_c, x, merged[cum_evap_col].values,
                             color=PALETTE["evap"], lw=2.0, label="cumul. evaporation")
        if cum_cond_col:
            _mpl_plot_series(ax_c, x, merged[cum_cond_col].values,
                             color=PALETTE["cond"], lw=2.0, label="cumul. condensation")
        if cum_latent_col:
            _mpl_plot_series(ax_c, x, merged[cum_latent_col].values,
                             color=PALETTE["latent"], lw=2.0, ls="--",
                             label="cumul. latent heating")
        ax_c.set_xlabel("Simulation step", fontsize=11)
        ax_c.set_ylabel("Cumulative (model units)", fontsize=10)
        ax_c.set_title("Cumulative evaporation, condensation & latent heating",
                       fontsize=12, fontweight="bold")
        ax_c.legend(); _x_formatter(ax_c)
        plt.tight_layout()

        pc_png = os.path.join(out_dir, "png",            "evap_cond_cumulative_only.png")
        pc_rpt = os.path.join(out_dir, "report_figures", "evap_cond_cumulative_only_300dpi.png")
        fig_c.savefig(pc_png, dpi=120, bbox_inches="tight")
        fig_c.savefig(pc_rpt, dpi=300, bbox_inches="tight")
        plt.close(fig_c)
        generated += [pc_png, pc_rpt]
        if verbose:
            print(f"  [OK] {os.path.relpath(pc_png)}")

    # ---- Combined 4-panel PNG -----------------------------------------
    n_panels = sum([has_rates, has_cum])
    n_panels = n_panels or 1
    fig_m = plt.figure(figsize=(13, 4.2 * n_panels))
    gs_m  = gridspec.GridSpec(n_panels, 1, hspace=0.45)
    pidx  = 0

    if has_rates:
        ax = fig_m.add_subplot(gs_m[pidx]); pidx += 1
        if evap_rate_col:
            _mpl_plot_series(ax, x, merged[evap_rate_col].values,
                             color=PALETTE["evap"], lw=1.8, label="evaporation rate")
        if cond_rate_col:
            _mpl_plot_series(ax, x, merged[cond_rate_col].values,
                             color=PALETTE["cond"], lw=1.8, label="condensation rate")
        if latent_col:
            _mpl_plot_series(ax, x, merged[latent_col].values,
                             color=PALETTE["latent"], lw=1.8, ls="--", label="latent heating")
        ax.set_ylabel("Rate / step", fontsize=9)
        ax.set_title("Instantaneous evaporation & condensation rates", fontsize=11)
        ax.legend(loc="upper right"); _x_formatter(ax)

    if has_cum:
        ax = fig_m.add_subplot(gs_m[pidx]); pidx += 1
        if cum_evap_col:
            _mpl_plot_series(ax, x, merged[cum_evap_col].values,
                             color=PALETTE["evap"], lw=2.0, label="cumul. evaporation")
        if cum_cond_col:
            _mpl_plot_series(ax, x, merged[cum_cond_col].values,
                             color=PALETTE["cond"], lw=2.0, label="cumul. condensation")
        if cum_latent_col:
            _mpl_plot_series(ax, x, merged[cum_latent_col].values,
                             color=PALETTE["latent"], lw=2.0, ls="--",
                             label="cumul. latent heating")
        ax.set_ylabel("Cumulative", fontsize=9)
        ax.set_title("Cumulative evaporation & condensation", fontsize=11)
        ax.legend(loc="upper left"); _x_formatter(ax)

    fig_m.text(0.5, 0.00, "Simulation step", ha="center", fontsize=11)
    fig_m.suptitle("Evaporation & condensation diagnostics",
                   fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()

    m_png = os.path.join(out_dir, "png",            "evap_cond_timeseries.png")
    m_rpt = os.path.join(out_dir, "report_figures", "evap_cond_timeseries_300dpi.png")
    fig_m.savefig(m_png, dpi=120, bbox_inches="tight")
    fig_m.savefig(m_rpt, dpi=300, bbox_inches="tight")
    plt.close(fig_m)
    generated += [m_png, m_rpt]
    if verbose:
        print(f"  [OK] {os.path.relpath(m_png)}")

    # ---- Plotly HTML --------------------------------------------------
    rows_t = []
    if has_rates: rows_t.append("Rates (per step)")
    if has_cum:   rows_t.append("Cumulative totals")
    n_rows = len(rows_t) or 1

    pfig = make_subplots(rows=n_rows, cols=1, subplot_titles=rows_t,
                         vertical_spacing=0.12)
    r = 1
    if has_rates:
        kw = dict(mode="markers+lines" if len(x) <= 3 else "lines")
        if evap_rate_col:
            pfig.add_trace(go.Scatter(x=x, y=merged[evap_rate_col].values,
                                      name="evaporation rate",
                                      line=dict(color=PALETTE["evap"]), **kw),
                           row=r, col=1)
        if cond_rate_col:
            pfig.add_trace(go.Scatter(x=x, y=merged[cond_rate_col].values,
                                      name="condensation rate",
                                      line=dict(color=PALETTE["cond"]), **kw),
                           row=r, col=1)
        if latent_col:
            pfig.add_trace(go.Scatter(x=x, y=merged[latent_col].values,
                                      name="latent heating rate",
                                      line=dict(color=PALETTE["latent"], dash="dash"), **kw),
                           row=r, col=1)
        r += 1

    if has_cum:
        kw = dict(mode="markers+lines" if len(x) <= 3 else "lines")
        if cum_evap_col:
            pfig.add_trace(go.Scatter(x=x, y=merged[cum_evap_col].values,
                                      name="cumul. evaporation",
                                      line=dict(color=PALETTE["evap"]), **kw),
                           row=r, col=1)
        if cum_cond_col:
            pfig.add_trace(go.Scatter(x=x, y=merged[cum_cond_col].values,
                                      name="cumul. condensation",
                                      line=dict(color=PALETTE["cond"]), **kw),
                           row=r, col=1)
        if cum_latent_col:
            pfig.add_trace(go.Scatter(x=x, y=merged[cum_latent_col].values,
                                      name="cumul. latent heating",
                                      line=dict(color=PALETTE["latent"], dash="dash"), **kw),
                           row=r, col=1)

    pfig.update_layout(
        height=max(380 * n_rows, 450),
        title="Evaporation & condensation diagnostics",
        template="plotly_white",
        showlegend=True,
    )
    html_path = os.path.join(out_dir, "html", "evap_cond_timeseries.html")
    pfig.write_html(html_path, include_plotlyjs=True)
    generated.append(html_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(html_path)}")

    # ---- Summary JSON -------------------------------------------------
    summary_ec: Dict[str, Any] = {}
    try:
        last = merged.iloc[-1]
        step_c = get_column(merged, "step")
        if step_c:        summary_ec["latest_step"]        = int(last[step_c])
        if evap_rate_col: summary_ec["latest_evap_rate"]   = float(last[evap_rate_col])
        if cond_rate_col: summary_ec["latest_cond_rate"]   = float(last[cond_rate_col])
        if cum_evap_col:  summary_ec["total_evaporation"]  = float(last[cum_evap_col])
        if cum_cond_col:  summary_ec["total_condensation"] = float(last[cum_cond_col])
    except Exception as exc:
        print(f"  [WARN] Evap/cond summary compute failed: {exc}")

    ec_json = os.path.join(out_dir, "summary", "evap_cond_summary.json")
    with open(ec_json, "w", encoding="utf-8") as fh:
        json.dump(summary_ec, fh, indent=2, default=str)
    generated.append(ec_json)
    if verbose:
        print(f"  [OK] {os.path.relpath(ec_json)}")

    return generated


# ------------------------------------------------------------------
# Moisture heatmaps (requires particle_spherical_step_*.csv)
# ------------------------------------------------------------------

def plot_humidity_heatmaps(
    input_dir: str,
    out_dir: str,
    max_particles: int = 5000,
    verbose: bool = False,
) -> List[str]:
    """
    Generate latitude–altitude heatmaps of q_p, relative humidity,
    condensation zones, and condensation overlay on Ψ.

    Requires particle_spherical_step_*.csv with columns:
        latitude, altitude, q_p, [q_sat]

    If the source file is absent, returns an empty list with a warning.
    """
    generated: List[str] = []

    # ---- Find latest particle_spherical file (numeric step order) ------
    latest = find_latest_file(input_dir, "particle_spherical_step_*.csv")
    if latest is None:
        latest = find_latest_file(input_dir, "particles_step_*.csv")
    if latest is None:
        print("  [WARN] No particle_spherical_step_*.csv found — skipping moisture heatmaps.")
        return generated

    if verbose:
        print(f"    Selected: {os.path.relpath(latest)}")

    # Print and check columns — diagnose alias mismatches before loading full data
    raw_cols = report_csv_columns(latest, "particle_spherical", verbose=verbose)
    if verbose:
        check_required_columns(
            raw_cols, ["latitude", "altitude", "q_p", "q_sat"],
            "particle_spherical", verbose=True,
        )

    df = read_csv_safe(latest)
    if df is None:
        return generated

    df = normalize_columns(df)
    df = downsample_dataframe(df, max_particles)

    lat_col  = get_column(df, "latitude")
    alt_col  = get_column(df, "altitude")
    qp_col   = get_column(df, "q_p")
    qsat_col = get_column(df, "q_sat")

    missing_keys = [k for k, v in [("latitude", lat_col),
                                    ("altitude", alt_col),
                                    ("q_p",      qp_col)] if v is None]
    if missing_keys:
        cols = list(df.columns)
        print(f"  [WARN] Required columns not found in {os.path.basename(latest)} — skipping moisture heatmaps.")
        print(f"         File columns  : {', '.join(cols)}")
        print(f"         Missing keys  : {', '.join(missing_keys)}")
        # Write missing-outputs report
        from plot_heatmaps import _write_missing_report
        _write_missing_report(
            out_dir,
            f"Moisture heatmaps ({os.path.basename(latest)})",
            cols, missing_keys,
        )
        return generated

    if qp_col is None:
        # lat/alt found but q_p missing — still skip moisture maps
        cols = list(df.columns)
        print(f"  [WARN] q_p column not found — skipping moisture heatmaps.")
        print(f"         File columns: {', '.join(cols)}")
        from plot_heatmaps import _write_missing_report
        _write_missing_report(out_dir,
                              f"Moisture heatmaps — q_p missing ({os.path.basename(latest)})",
                              cols, ["q_p"])
        return generated

    lat  = pd.to_numeric(df[lat_col], errors="coerce").values
    alt  = pd.to_numeric(df[alt_col], errors="coerce").values
    qp   = pd.to_numeric(df[qp_col],  errors="coerce").values

    # Drop rows where any required coordinate or value is NaN
    valid_mask = np.isfinite(lat) & np.isfinite(alt) & np.isfinite(qp)
    lat, alt, qp = lat[valid_mask], alt[valid_mask], qp[valid_mask]

    step = extract_step_from_filename(latest)

    if len(qp) == 0:
        print("  [WARN] No finite q_p values after filtering — skipping humidity heatmap.")
        return generated

    # ---- Percentile-based color limits (avoid blank plots) ------------
    qp_p02  = float(np.percentile(qp, 2))
    qp_p98  = float(np.percentile(qp, 98))
    qp_min  = float(qp.min())
    qp_max  = float(qp.max())
    qp_mean = float(qp.mean())

    # Fall back to min/max if percentile range collapses (< 10% of span)
    if qp_p98 - qp_p02 < 0.1 * (qp_max - qp_min + 1e-30):
        vmin_qp, vmax_qp = qp_min, qp_max
    else:
        vmin_qp, vmax_qp = qp_p02, qp_p98

    if verbose:
        print(f"    q_p  min={qp_min:.6g}  max={qp_max:.6g}  mean={qp_mean:.6g}")
        print(f"    q_p  2%={qp_p02:.6g}  98%={qp_p98:.6g}")
        print(f"    color limits: vmin={vmin_qp:.6g}  vmax={vmax_qp:.6g}")

    # ---- Bin into lat × alt grid (36 × 20) ----------------------------
    n_lat, n_alt = 36, 20
    lat_edges = np.linspace(lat.min(), lat.max(), n_lat + 1)
    alt_edges = np.linspace(alt.min(), alt.max(), n_alt + 1)
    lat_bins  = np.clip(np.digitize(lat, lat_edges[:-1]) - 1, 0, n_lat - 1)
    alt_bins  = np.clip(np.digitize(alt, alt_edges[:-1]) - 1, 0, n_alt - 1)

    # Must initialise to ZERO so np.add.at accumulates correctly.
    # (np.nan + x = NaN, which destroys all data.)
    qp_sum   = np.zeros((n_alt, n_lat))
    qp_count = np.zeros((n_alt, n_lat))
    np.add.at(qp_sum,   (alt_bins, lat_bins), qp)
    np.add.at(qp_count, (alt_bins, lat_bins), 1)
    with np.errstate(invalid="ignore"):
        qp_grid = np.where(qp_count > 0, qp_sum / qp_count, np.nan)

    lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    alt_centers = 0.5 * (alt_edges[:-1] + alt_edges[1:])

    finite_grid = qp_grid[np.isfinite(qp_grid)]
    if verbose:
        print(f"    Grid shape: {qp_grid.shape}  "
              f"finite cells: {len(finite_grid)}/{qp_grid.size}")

    range_str = f"{qp_min:.4g} – {qp_max:.4g}"
    colorbar_label = "Specific humidity q_p"

    set_mpl_style()

    def _save_heatmap(grid, cmap, clabel, fname_stem, title, vmin=None, vmax=None):
        """Save matplotlib heatmap at 120 DPI (PNG) and 300 DPI (report)."""
        _g = []
        fig, ax = plt.subplots(figsize=(10, 6))
        kwargs = dict(cmap=cmap, shading="auto")
        if vmin is not None:
            kwargs["vmin"] = vmin
        if vmax is not None:
            kwargs["vmax"] = vmax
        masked = np.ma.masked_invalid(grid)
        im = ax.pcolormesh(lat_centers, alt_centers, masked, **kwargs)
        cb = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
        cb.set_label(clabel, fontsize=10)
        ax.set_xlabel("Latitude [deg]",      fontsize=11)
        ax.set_ylabel("Altitude [model units]", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        plt.tight_layout()
        p  = os.path.join(out_dir, "png",            fname_stem + ".png")
        rp = os.path.join(out_dir, "report_figures", fname_stem + "_300dpi.png")
        fig.savefig(p,  dpi=120, bbox_inches="tight")
        fig.savefig(rp, dpi=300, bbox_inches="tight")
        plt.close(fig)
        _g += [p, rp]
        if verbose:
            print(f"  [OK] {os.path.relpath(p)}")
        return _g

    # ---- q_p heatmap (sequential scale) -------------------------------
    title_qp = (
        f"Specific humidity q\u209A — latitude × altitude (step {step:,})\n"
        f"q\u209A range: {range_str}  |  moisture diagnostic — simulation output"
    )
    generated += _save_heatmap(
        qp_grid,
        cmap="YlGnBu",
        clabel=colorbar_label,
        fname_stem="humidity_lat_alt_heatmap",
        title=title_qp,
        vmin=vmin_qp,
        vmax=vmax_qp,
    )

    # ---- Save binned CSV ----------------------------------------------
    grid_df = pd.DataFrame(
        [(float(lat_centers[j]), float(alt_centers[i]), float(qp_grid[i, j]))
         for i in range(n_alt) for j in range(n_lat)],
        columns=["latitude_deg", "altitude", "mean_qp"],
    )
    grid_csv = os.path.join(out_dir, "summary", "computed_qp_grid.csv")
    grid_df.to_csv(grid_csv, index=False)
    generated.append(grid_csv)

    # ---- Plotly interactive q_p heatmap --------------------------------
    pfig = go.Figure(go.Heatmap(
        x=lat_centers.tolist(),
        y=alt_centers.tolist(),
        z=qp_grid.tolist(),
        colorscale="YlGnBu",
        zmin=vmin_qp, zmax=vmax_qp,
        colorbar=dict(title=colorbar_label),
        hoverongaps=False,
    ))
    pfig.update_layout(
        title=dict(
            text=(
                f"Specific humidity q\u209A — latitude × altitude (step {step:,})<br>"
                f"<sup>q\u209A range: {range_str} | moisture diagnostic</sup>"
            ),
            font=dict(size=15),
        ),
        xaxis_title="Latitude [deg]",
        yaxis_title="Altitude [model units]",
        template="plotly_white",
        margin=dict(l=60, r=40, t=90, b=60),
    )
    qp_html = os.path.join(out_dir, "html", "humidity_lat_alt_heatmap.html")
    pfig.write_html(qp_html, include_plotlyjs=True)
    generated.append(qp_html)
    if verbose:
        print(f"  [OK] {os.path.relpath(qp_html)}")

    # Relative humidity and condensation mask (require q_sat)
    if qsat_col is None:
        print("  [INFO] q_sat column missing — RH and condensation mask skipped; q_p heatmap generated.")
        return generated

    # q_sat must be filtered with the same valid_mask used for qp
    qsat_raw = pd.to_numeric(df[qsat_col], errors="coerce").values[valid_mask]
    with np.errstate(divide="ignore", invalid="ignore"):
        rh = np.where(qsat_raw > 0, qp / qsat_raw, np.nan)
    rh = np.clip(rh, 0, None)

    rh_valid = np.isfinite(rh)
    rh_sum   = np.zeros((n_alt, n_lat))   # init to 0, NOT NaN
    rh_count = np.zeros((n_alt, n_lat))
    np.add.at(rh_sum,   (alt_bins[rh_valid], lat_bins[rh_valid]), rh[rh_valid])
    np.add.at(rh_count, (alt_bins[rh_valid], lat_bins[rh_valid]), 1)
    with np.errstate(invalid="ignore"):
        rh_grid = np.where(rh_count > 0, rh_sum / rh_count, np.nan)

    generated += _save_heatmap(
        rh_grid, "Blues", "Relative humidity (q_p / q_sat)",
        "relative_humidity_heatmap",
        f"Relative humidity — latitude–altitude (step {step:,})\n"
        "(moisture diagnostic — simulation output)",
    )

    cond_mask  = (qp > qsat).astype(float)
    cm_grid    = np.full((n_alt, n_lat), np.nan)
    cm_count   = np.zeros((n_alt, n_lat))
    np.add.at(cm_grid,  (alt_bins, lat_bins), cond_mask)
    np.add.at(cm_count, (alt_bins, lat_bins), 1)
    with np.errstate(invalid="ignore"):
        cm_grid = np.where(cm_count > 0, cm_grid / cm_count, np.nan)

    generated += _save_heatmap(
        cm_grid, "Reds", "Condensation fraction (q_p > q_sat)",
        "condensation_zones_heatmap",
        f"Condensation zones — latitude–altitude (step {step:,})\n"
        "(fraction of particles with q_p > q_sat)",
    )

    return generated
