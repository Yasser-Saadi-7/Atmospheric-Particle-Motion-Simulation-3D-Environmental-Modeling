"""
plot_particles_3d.py — Stage UI-4.1
==========================================================
Generates professional interactive 3D particle shell viewers.

Source file priority:
  1. particle_spherical_step_*.csv  (spherical coords preferred)
  2. particles_step_*.csv           (Cartesian fallback)

Generated outputs (only for columns that exist):
  html/particle_3d_temperature.html
  html/particle_3d_vr.html
  html/particle_3d_vtheta.html
  html/particle_3d_qp.html

  png/particle_preview_temperature.png   (via particle_preview_builder.py)
  png/particle_preview_vr.png

Gallery x-z previews are generated separately by particle_preview_builder.py.
All HTML pages use the professional layout from plotly_3d_style.py.
==========================================================
"""

import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from data_loader import (
    read_csv_safe, normalize_columns, get_column,
    find_latest_file, downsample_dataframe,
    extract_step_from_filename,
)
from plotly_3d_style import (
    VARIABLE_CONFIG, VIEWER_MODES,
    DEFAULT_INNER_RADIUS, DEFAULT_OUTER_RADIUS,
    get_color_config, get_marker_size, get_scene_style, get_camera,
    build_planet_traces, build_hover_data,
    write_viewer_page,
)


# ──────────────────────────────────────────────────────────────────────────
# Coordinate helpers
# ──────────────────────────────────────────────────────────────────────────

def _load_particle_xyz(
    df: pd.DataFrame,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Extract X, Y, Z arrays from the DataFrame.

    For spherical files: compute Cartesian from radius, lat, lon columns.
    For Cartesian files: use x, y, z directly.
    """
    r_col   = get_column(df, "radius")
    lat_col = get_column(df, "latitude")
    lon_col = get_column(df, "longitude")

    if r_col and lat_col and lon_col:
        r     = df[r_col].values.astype(float)
        theta = df[lat_col].values.astype(float)
        phi   = df[lon_col].values.astype(float)
        x = r * np.cos(np.radians(theta)) * np.cos(np.radians(phi))
        y = r * np.cos(np.radians(theta)) * np.sin(np.radians(phi))
        z = r * np.sin(np.radians(theta))
        return x, y, z

    x_col = get_column(df, "x")
    y_col = get_column(df, "y")
    z_col = get_column(df, "z")
    if x_col and y_col and z_col:
        return (df[x_col].values.astype(float),
                df[y_col].values.astype(float),
                df[z_col].values.astype(float))

    return None


def _infer_radii(df: pd.DataFrame) -> Tuple[float, float]:
    """Infer inner/outer shell radius from radius column, fallback to defaults."""
    r_col = get_column(df, "radius")
    if r_col:
        rvals = df[r_col].values.astype(float)
        finite = rvals[np.isfinite(rvals)]
        if len(finite) >= 10:
            return (float(np.percentile(finite, 2)),
                    float(np.percentile(finite, 98)))
    return DEFAULT_INNER_RADIUS, DEFAULT_OUTER_RADIUS


# ──────────────────────────────────────────────────────────────────────────
# Plotly figure builder
# ──────────────────────────────────────────────────────────────────────────

def _build_3d_viewer(
    df: pd.DataFrame,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    var_name: str,
    step: int,
    inner_r: float,
    outer_r: float,
) -> Optional[go.Figure]:
    """Build a professional Plotly 3D scatter figure for one variable."""
    col = get_column(df, var_name)
    if col is None:
        return None

    vals = df[col].values.astype(float)
    n    = len(vals)

    colorscale, cmin, cmax = get_color_config(var_name, vals)
    msize  = get_marker_size(n)
    vcfg   = VARIABLE_CONFIG.get(var_name, {})
    cb_title = vcfg.get("label", var_name) + "<br>" + vcfg.get("units", "")

    # Rich hover text
    try:
        custom, hover_tmpl = build_hover_data(df, col)
    except Exception:
        custom, hover_tmpl = None, "%{text}<extra></extra>"

    particle_trace = go.Scatter3d(
        x=x, y=y, z=z,
        mode="markers",
        marker=dict(
            size=msize,
            color=vals,
            colorscale=colorscale,
            cmin=cmin,
            cmax=cmax,
            colorbar=dict(
                title=dict(text=cb_title, font=dict(color="#0F172A", size=12)),
                tickfont=dict(color="#0F172A", size=10),
                thickness=16,
                outlinecolor="#D1D5DB",
                outlinewidth=1,
                bgcolor="rgba(255,255,255,0.85)",
            ),
            opacity=0.85,
            line=dict(width=0),
        ),
        customdata=custom,
        hovertemplate=hover_tmpl,
        name="Particles",
        showlegend=False,
    )

    # Build figure with planet reference as additional traces
    planet_traces = build_planet_traces(inner_r, outer_r)
    fig = go.Figure(data=[particle_trace] + planet_traces)

    # Apply scene layout
    scene = get_scene_style(outer_r)
    fig.update_layout(
        scene=scene,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#0F172A", family="Inter, Roboto, system-ui, sans-serif"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=700,
        showlegend=False,
    )

    return fig


# ──────────────────────────────────────────────────────────────────────────
# Main public function
# ──────────────────────────────────────────────────────────────────────────

def plot_3d_viewers(
    input_dir: str,
    out_dir: str,
    max_particles: int = 5000,
    verbose: bool = False,
) -> List[str]:
    """Generate professional interactive 3D particle shell viewers.

    Returns list of created file paths.
    """
    generated: List[str] = []

    # ── Find source CSV ───────────────────────────────────────────────────
    latest = find_latest_file(input_dir, "particle_spherical_step_*.csv")
    if latest is None:
        latest = find_latest_file(input_dir, "particles_step_*.csv")
    if latest is None:
        print("  [WARN] No particle snapshot file found — skipping 3D viewers.")
        return generated

    if verbose:
        print(f"  [3D] Source: {os.path.relpath(latest)}")

    df = read_csv_safe(latest)
    if df is None:
        return generated

    df   = normalize_columns(df)
    df   = downsample_dataframe(df, max_particles)
    step = extract_step_from_filename(latest) or 0

    xyz = _load_particle_xyz(df)
    if xyz is None:
        print(f"  [WARN] No position columns found in {latest} — skipping.")
        return generated

    x, y, z = xyz
    n = len(x)
    inner_r, outer_r = _infer_radii(df)

    if verbose:
        print(f"  [3D] Step={step:,}  particles={n:,}  "
              f"inner_r={inner_r:.1f}  outer_r={outer_r:.1f}")

    # ── Per-variable viewer generation ───────────────────────────────────
    modes = [
        ("T_p",     "particle_3d_temperature"),
        ("v_r",     "particle_3d_vr"),
        ("v_theta", "particle_3d_vtheta"),
        ("q_p",     "particle_3d_qp"),
    ]

    for var_name, stem in modes:
        pfig = _build_3d_viewer(df, x, y, z, var_name, step, inner_r, outer_r)
        if pfig is None:
            if verbose:
                print(f"  [INFO] Column '{var_name}' missing — skipping {stem}.")
            continue

        html_out = os.path.join(out_dir, "html", f"{stem}.html")

        # Write professional page via shared module
        try:
            write_viewer_page(
                fig=pfig,
                out_path=html_out,
                var_name=var_name,
                step=step,
                n_particles=n,
                inner_r=inner_r,
                outer_r=outer_r,
            )
            generated.append(html_out)
            if verbose:
                print(f"  [OK] {os.path.relpath(html_out)}")
        except Exception as exc:
            print(f"  [ERROR] Writing {stem}.html failed: {exc}")
            continue

    # ── x-z gallery previews (temperature + radial velocity) ──────────────
    from particle_preview_builder import generate_static_previews
    preview_files = generate_static_previews(
        input_dir, out_dir, max_particles=max_particles, verbose=verbose,
    )
    generated.extend(preview_files)

    return generated
