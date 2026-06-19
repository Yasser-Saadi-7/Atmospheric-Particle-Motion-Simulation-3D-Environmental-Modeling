"""
plot_heatmaps.py — Stage UI-3
==========================================================
Generates latitude–altitude heatmap diagnostics:
  • Streamfunction Ψ heatmap with contours
  • Meridional wind v_theta heatmap
  • Latitude–altitude temperature heatmap

Each function handles missing source files gracefully and
returns a list of created file paths.
==========================================================
"""

import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from typing import List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import plotly.graph_objects as go

from data_loader import (
    read_csv_safe, normalize_columns, get_column,
    find_latest_file, find_step_files,
    downsample_dataframe, extract_step_from_filename,
    report_csv_columns, check_required_columns,
    set_mpl_style, PALETTE,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _pivot_to_grid(
    df: pd.DataFrame,
    lat_col: str,
    alt_col: str,
    val_col: str,
    n_lat: int = 36,
    n_alt: int = 20,
):
    """Bin a particle DataFrame into a (n_alt × n_lat) mean-value grid."""
    lat = df[lat_col].values
    alt = df[alt_col].values
    val = df[val_col].values

    lat_edges = np.linspace(lat.min(), lat.max(), n_lat + 1)
    alt_edges = np.linspace(alt.min(), alt.max(), n_alt + 1)
    lat_bins  = np.clip(np.digitize(lat, lat_edges[:-1]) - 1, 0, n_lat - 1)
    alt_bins  = np.clip(np.digitize(alt, alt_edges[:-1]) - 1, 0, n_alt - 1)

    grid  = np.full((n_alt, n_lat), np.nan)
    count = np.zeros((n_alt, n_lat))
    np.add.at(grid,  (alt_bins, lat_bins), np.where(np.isnan(val), 0, val))
    np.add.at(count, (alt_bins, lat_bins), 1)
    with np.errstate(invalid="ignore"):
        grid = np.where(count > 0, grid / count, np.nan)

    lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    alt_centers = 0.5 * (alt_edges[:-1] + alt_edges[1:])
    return grid, lat_centers, alt_centers


def _mpl_heatmap(
    grid, lat_c, alt_c, cmap,
    xlabel, ylabel, clabel, title,
    add_contours=False,
    vmin=None, vmax=None,
):
    """
    Create a matplotlib heatmap figure and return (fig, ax).
    Pass vmin/vmax for explicit color scale; if omitted they are derived
    from the data (symmetric for diverging colormaps when both are None).
    """
    set_mpl_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    masked = np.ma.masked_invalid(grid)
    kwargs = dict(cmap=cmap, shading="auto")
    if vmin is not None:
        kwargs["vmin"] = vmin
    if vmax is not None:
        kwargs["vmax"] = vmax

    im = ax.pcolormesh(lat_c, alt_c, masked, **kwargs)
    cb = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label(clabel, fontsize=10)

    if add_contours:
        filled = np.nan_to_num(grid, nan=0.0)
        cs = ax.contour(lat_c, alt_c, filled,
                        levels=10, colors="k", linewidths=0.7, alpha=0.6)
        ax.clabel(cs, inline=True, fontsize=7, fmt="%.2g")

    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    return fig, ax


def _save_pair(fig, out_dir, subfolder_file, report_file, verbose):
    """Save PNG at 120 DPI and 300 DPI."""
    generated = []
    png_path = os.path.join(out_dir, "png",            subfolder_file)
    rpt_path = os.path.join(out_dir, "report_figures", report_file)
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    fig.savefig(rpt_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    generated += [png_path, rpt_path]
    if verbose:
        print(f"  [OK] {os.path.relpath(png_path)}")
    return generated


# ------------------------------------------------------------------
# Streamfunction heatmap
# ------------------------------------------------------------------

def _write_missing_report(out_dir: str, label: str, cols: List[str],
                          missing_keys: List[str]) -> None:
    """Append a skipped-plot entry to summary/missing_required_outputs.md."""
    md_path = os.path.join(out_dir, "summary", "missing_required_outputs.md")
    from data_loader import COLUMN_ALIASES
    with open(md_path, "a", encoding="utf-8") as fh:
        fh.write(f"\n## {label}\n\n")
        fh.write(f"**Actual columns in file:**\n```\n{', '.join(cols)}\n```\n\n")
        fh.write("**Missing required aliases:**\n\n")
        for key in missing_keys:
            aliases = COLUMN_ALIASES.get(key, [key])
            fh.write(f"- `{key}`: tried `{', '.join(aliases)}`\n")
        fh.write("\n")


def plot_streamfunction(
    input_dir: str,
    out_dir: str,
    verbose: bool = False,
) -> List[str]:
    """
    Generate streamfunction Ψ heatmap with contours.
    Source priority:
      1. streamfunction_step_*.csv  (lat/latitude_center_deg, alt/altitude_center, psi)
      2. streamfunction_grid_*.csv  fallback
    """
    generated: List[str] = []

    # ---- Find source file (numeric step order) -----------------------
    latest = find_latest_file(input_dir, "streamfunction_step_*.csv")
    if latest is None:
        latest = find_latest_file(input_dir, "streamfunction_grid_*.csv")
    if latest is None:
        print("  [WARN] streamfunction_step_*.csv not found — skipping streamfunction heatmap.")
        return generated

    if verbose:
        print(f"    Selected: {os.path.relpath(latest)}")

    # Report CSV columns to help debug alias mismatches
    raw_cols = report_csv_columns(latest, "streamfunction_step", verbose=verbose)
    if verbose:
        col_check = check_required_columns(raw_cols, ["lat", "alt", "psi"],
                                           "streamfunction_step", verbose=True)

    df = read_csv_safe(latest)
    if df is None:
        return generated

    df = normalize_columns(df)
    lat_col = get_column(df, "lat")
    alt_col = get_column(df, "alt")
    psi_col = get_column(df, "psi")

    if lat_col is None or alt_col is None or psi_col is None:
        missing_keys = [k for k, v in [("lat", lat_col), ("alt", alt_col), ("psi", psi_col)]
                        if v is None]
        cols = list(df.columns)
        print(f"  [WARN] Required columns not found in {os.path.basename(latest)} — skipping.")
        print(f"         File columns  : {', '.join(cols)}")
        print(f"         Missing keys  : {', '.join(missing_keys)}")
        _write_missing_report(out_dir, f"Streamfunction heatmap ({os.path.basename(latest)})",
                              cols, missing_keys)
        return generated

    step = extract_step_from_filename(latest)

    # Check if data is already a grid (unique lat × unique alt) or scatter
    n_uniq_lat = df[lat_col].nunique()
    n_uniq_alt = df[alt_col].nunique()

    if n_uniq_lat * n_uniq_alt == len(df):
        # Already a grid: pivot directly
        pivot = df.pivot_table(index=alt_col, columns=lat_col, values=psi_col)
        grid      = pivot.values
        lat_c     = pivot.columns.values
        alt_c     = pivot.index.values
    else:
        # Scatter: bin into grid
        grid, lat_c, alt_c = _pivot_to_grid(df, lat_col, alt_col, psi_col)

    title = (
        f"Streamfunction diagnostic — candidate meridional circulation (step {step:,})\n"
        f"Ψ latitude–altitude heatmap with contours"
    )
    fig, _ = _mpl_heatmap(
        grid, lat_c, alt_c,
        cmap="RdBu_r",
        xlabel="Latitude (model units)",
        ylabel="Altitude (model units)",
        clabel="Streamfunction Ψ (model units)",
        title=title,
        add_contours=True,
    )
    generated += _save_pair(
        fig, out_dir,
        "streamfunction_heatmap_contours.png",
        "streamfunction_heatmap_contours_300dpi.png",
        verbose,
    )

    # ---- Plotly interactive ------------------------------------------
    pfig = go.Figure()
    pfig.add_trace(go.Heatmap(
        x=lat_c.tolist(), y=alt_c.tolist(),
        z=grid.tolist(),
        colorscale="RdBu_r",
        colorbar=dict(title="Ψ"),
        hoverongaps=False,
        reversescale=False,
    ))
    # Plotly contour overlay
    pfig.add_trace(go.Contour(
        x=lat_c.tolist(), y=alt_c.tolist(),
        z=grid.tolist(),
        showscale=False,
        contours=dict(coloring="none", showlabels=True),
        line=dict(width=0.8, color="black"),
        opacity=0.7,
    ))
    pfig.update_layout(
        title=dict(
            text=f"Streamfunction Ψ diagnostic (step {step:,})<br>"
                 "<sup>Candidate meridional circulation structure — not a proven cell identification</sup>",
            font=dict(size=15),
        ),
        xaxis_title="Latitude (model units)",
        yaxis_title="Altitude (model units)",
        template="plotly_white",
        margin=dict(l=60, r=40, t=90, b=60),
    )
    html_path = os.path.join(out_dir, "html", "streamfunction_heatmap_contours.html")
    pfig.write_html(html_path, include_plotlyjs=True)
    generated.append(html_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(html_path)}")

    return generated


# ------------------------------------------------------------------
# Meridional wind v_theta heatmap
# ------------------------------------------------------------------

def plot_vtheta_heatmap(
    input_dir: str,
    out_dir: str,
    max_particles: int = 5000,
    verbose: bool = False,
) -> List[str]:
    """
    Generate mean v_theta (meridional wind) heatmap.

    Source priority:
      1. circulation_accum_step_*.csv  (pre-binned grid, preferred)
      2. particle_spherical_step_*.csv (scatter → bin on the fly)
      3. particles_step_*.csv          (scatter → bin on the fly)

    For pre-binned data the pivot is computed with pd.pivot_table so
    that the data are not re-binned (which can cause blank plots).
    A symmetric color scale is always used for the diverging palette.
    """
    generated: List[str] = []

    # ---- Select source file -------------------------------------------
    latest = find_latest_file(input_dir, "circulation_accum_step_*.csv")
    source_type = "precomputed"
    if latest is None:
        latest = find_latest_file(input_dir, "particle_spherical_step_*.csv")
        source_type = "computed"
    if latest is None:
        latest = find_latest_file(input_dir, "particles_step_*.csv")
        source_type = "computed"
    if latest is None:
        print("  [WARN] No circulation_accum or particle file found — skipping v_theta heatmap.")
        return generated

    if verbose:
        print(f"    Selected ({source_type}): {os.path.relpath(latest)}")

    raw_cols = report_csv_columns(latest, "circulation/particle", verbose=verbose)
    if verbose:
        check_required_columns(raw_cols, ["latitude", "altitude", "v_theta"],
                               "circulation/particle", verbose=True)

    df = read_csv_safe(latest)
    if df is None:
        return generated

    df = normalize_columns(df)

    # Resolve column names via broad aliases (includes latitude_center_deg, mean_v_theta, etc.)
    lat_col    = get_column(df, "latitude")
    alt_col    = get_column(df, "altitude")
    vtheta_col = get_column(df, "v_theta")

    if lat_col is None or alt_col is None or vtheta_col is None:
        missing_keys = [k for k, v in [("latitude", lat_col),
                                        ("altitude", alt_col),
                                        ("v_theta",  vtheta_col)] if v is None]
        cols = list(df.columns)
        print(f"  [WARN] Required columns not found in {os.path.basename(latest)} — skipping.")
        print(f"         File columns  : {', '.join(cols)}")
        print(f"         Missing keys  : {', '.join(missing_keys)}")
        _write_missing_report(out_dir, f"v_theta heatmap ({os.path.basename(latest)})",
                              cols, missing_keys)
        return generated

    # ---- Force numeric types -----------------------------------------
    df[lat_col]    = pd.to_numeric(df[lat_col],    errors="coerce")
    df[alt_col]    = pd.to_numeric(df[alt_col],    errors="coerce")
    df[vtheta_col] = pd.to_numeric(df[vtheta_col], errors="coerce")
    df = df.dropna(subset=[lat_col, alt_col, vtheta_col])

    step = extract_step_from_filename(latest)

    # ---- Build grid --------------------------------------------------
    n_uniq_lat = df[lat_col].nunique()
    n_uniq_alt = df[alt_col].nunique()

    if source_type == "precomputed" and n_uniq_lat * n_uniq_alt == len(df):
        # Data is already a regular grid → pivot directly, no re-binning
        pivot = df.pivot_table(
            index=alt_col,
            columns=lat_col,
            values=vtheta_col,
            aggfunc="mean",
        )
        pivot = pivot.sort_index(axis=0).sort_index(axis=1)
        pivot = pivot.dropna(how="all", axis=0).dropna(how="all", axis=1)
        grid  = pivot.values.astype(float)
        lat_c = np.array(pivot.columns, dtype=float)
        alt_c = np.array(pivot.index,   dtype=float)
    else:
        # Scatter data: downscale then bin
        if source_type == "computed":
            df = downsample_dataframe(df, max_particles)
        grid, lat_c, alt_c = _pivot_to_grid(df, lat_col, alt_col, vtheta_col)

    # ---- Verbose diagnostics ----------------------------------------
    finite = grid[np.isfinite(grid)]
    if verbose:
        print(f"    Grid shape           : {grid.shape}")
        print(f"    Finite value count   : {len(finite)}")
        if len(finite):
            print(f"    min / max / |max|    : "
                  f"{finite.min():.6f} / {finite.max():.6f} / {np.abs(finite).max():.6f}")
        print(f"    Unique lat bins      : {len(lat_c)}")
        print(f"    Unique alt bins      : {len(alt_c)}")

    if len(finite) == 0:
        print("  [WARN] v_theta grid has no finite values — skipping heatmap.")
        return generated

    # ---- Symmetric color scale around zero ---------------------------
    vabs = float(np.abs(finite).max())
    vmax_sym = vabs if vabs > 0 else 1e-6
    vmin_sym = -vmax_sym

    # ---- Save grid CSV -----------------------------------------------
    rows = [(float(lat_c[j]), float(alt_c[i]), float(grid[i, j]))
            for i in range(len(alt_c)) for j in range(len(lat_c))]
    grid_df = pd.DataFrame(rows, columns=["latitude_deg", "altitude", "mean_vtheta"])
    csv_out = os.path.join(out_dir, "summary", "computed_vtheta_grid.csv")
    grid_df.to_csv(csv_out, index=False)
    generated.append(csv_out)

    source_label = "pre-binned accumulator" if source_type == "precomputed" else "computed from particles"
    title_mpl = (
        f"Mean meridional wind v_θ — latitude × altitude (step {step:,})\n"
        f"Simulation diagnostic ({source_label})"
    )

    # ---- Matplotlib PNG ---------------------------------------------
    fig, _ = _mpl_heatmap(
        grid, lat_c, alt_c,
        cmap="coolwarm",
        xlabel="Latitude [deg]",
        ylabel="Altitude [model units]",
        clabel="Mean meridional velocity v_θ (model units)",
        title=title_mpl,
        vmin=vmin_sym,
        vmax=vmax_sym,
    )
    generated += _save_pair(
        fig, out_dir,
        "vtheta_heatmap.png",
        "vtheta_heatmap_300dpi.png",
        verbose,
    )

    # ---- Plotly HTML -------------------------------------------------
    pfig = go.Figure(go.Heatmap(
        x=lat_c.tolist(), y=alt_c.tolist(),
        z=grid.tolist(),
        colorscale="RdBu",
        zmid=0,
        zmin=vmin_sym, zmax=vmax_sym,
        colorbar=dict(title="v_θ (model units)"),
        hoverongaps=False,
    ))
    pfig.update_layout(
        title=dict(
            text=(
                f"Mean meridional wind v_θ — latitude × altitude (step {step:,})<br>"
                "<sup>Simulation diagnostic — not a real wind speed calibration</sup>"
            ),
            font=dict(size=15),
        ),
        xaxis_title="Latitude [deg]",
        yaxis_title="Altitude [model units]",
        template="plotly_white",
        margin=dict(l=60, r=40, t=90, b=60),
    )
    html_path = os.path.join(out_dir, "html", "vtheta_heatmap.html")
    pfig.write_html(html_path, include_plotlyjs=True)
    generated.append(html_path)
    if verbose:
        print(f"  [OK] {os.path.relpath(html_path)}")

    return generated


# ------------------------------------------------------------------
# Latitude–altitude temperature heatmap
# ------------------------------------------------------------------

def plot_temperature_lat_alt(
    input_dir: str,
    out_dir: str,
    max_particles: int = 5000,
    verbose: bool = False,
) -> List[str]:
    """
    Generate latitude–altitude temperature heatmap from
    particle_spherical_step_*.csv or particles_step_*.csv.
    """
    generated: List[str] = []

    latest = find_latest_file(input_dir, "particle_spherical_step_*.csv")
    if latest is None:
        latest = find_latest_file(input_dir, "particles_step_*.csv")
    if latest is None:
        print("  [WARN] No particle file found for temperature lat-alt heatmap — skipping.")
        return generated

    df = read_csv_safe(latest)
    if df is None:
        return generated

    df = normalize_columns(df)
    df = downsample_dataframe(df, max_particles)

    lat_col  = get_column(df, "latitude")
    alt_col  = get_column(df, "altitude")
    temp_col = get_column(df, "T_p")

    if lat_col is None or alt_col is None or temp_col is None:
        cols = list(df.columns)
        print("  [WARN] lat / alt / T_p columns not found — skipping temperature lat-alt heatmap.")
        print(f"         File columns: {', '.join(cols)}")
        return generated

    step = extract_step_from_filename(latest)
    grid, lat_c, alt_c = _pivot_to_grid(df, lat_col, alt_col, temp_col)

    fig, _ = _mpl_heatmap(
        grid, lat_c, alt_c,
        cmap="plasma",
        xlabel="Latitude (model units)",
        ylabel="Altitude (model units)",
        clabel="Mean temperature T_p (model units)",
        title=(
            f"Temperature field — latitude–altitude (step {step:,})\n"
            "Simulation diagnostic"
        ),
    )
    generated += _save_pair(
        fig, out_dir,
        "temperature_lat_alt_heatmap.png",
        "temperature_lat_alt_heatmap_300dpi.png",
        verbose,
    )
    return generated
