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

  png/particle_3d_temperature_preview.png
  png/particle_3d_vr_preview.png
  animations/particle_animation_preview.png   (temperature preview)

All pages use the professional layout from plotly_3d_style.py.
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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from data_loader import (
    read_csv_safe, normalize_columns, get_column,
    find_latest_file, downsample_dataframe,
    extract_step_from_filename, set_mpl_style,
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
# Preview PNG (matplotlib)
# ──────────────────────────────────────────────────────────────────────────

def _mpl_preview(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    color_vals: np.ndarray,
    color_label: str,
    var_name: str,
    title: str,
    png_path: str,
    dpi: int = 120,
) -> bool:
    """Save a matplotlib 3D preview PNG with professional light background."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)
        _, cmin, cmax = get_color_config(var_name, color_vals)
        mpl_cmap = {
            "T_p":    "plasma",
            "v_r":    "RdBu_r",
            "v_theta":"RdBu_r",
            "q_p":    "YlGnBu",
        }.get(var_name, "plasma")

        set_mpl_style()
        fig = plt.figure(figsize=(7, 7), facecolor="#F8FAFC")
        ax  = fig.add_subplot(111, projection="3d")
        sc  = ax.scatter(x, y, z, c=color_vals, cmap=mpl_cmap,
                         vmin=cmin, vmax=cmax,
                         s=2.5, alpha=0.82, linewidths=0)
        cb = plt.colorbar(sc, ax=ax, shrink=0.52, pad=0.04, label=color_label)
        cb.ax.tick_params(labelsize=8, colors="#1E293B")
        cb.set_label(color_label, fontsize=9, color="#1E293B")
        ax.set_title(title, fontsize=10, fontweight="bold",
                     color="#0F172A", pad=6)
        ax.set_axis_off()
        ax.set_facecolor("#F8FAFC")
        fig.patch.set_facecolor("#F8FAFC")
        ax.view_init(elev=20, azim=45)
        plt.tight_layout(pad=0.5)
        fig.savefig(png_path, dpi=dpi, bbox_inches="tight",
                    facecolor="#F8FAFC")
        plt.close(fig)
        return True
    except Exception as exc:
        plt.close("all")
        print(f"  [WARN] 3D preview PNG failed ({os.path.basename(png_path)}): {exc}")
        return False


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
        ("T_p",     "particle_3d_temperature", "png/particle_3d_temperature_preview.png"),
        ("v_r",     "particle_3d_vr",           "png/particle_3d_vr_preview.png"),
        ("v_theta", "particle_3d_vtheta",        None),
        ("q_p",     "particle_3d_qp",            None),
    ]

    for var_name, stem, preview_png in modes:
        pfig = _build_3d_viewer(df, x, y, z, var_name, step, inner_r, outer_r)
        if pfig is None:
            if verbose:
                print(f"  [INFO] Column '{var_name}' missing — skipping {stem}.")
            continue

        vcfg     = VARIABLE_CONFIG.get(var_name, {})
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

        # ── Preview PNG ───────────────────────────────────────────────────
        if preview_png:
            col = get_column(df, var_name)
            if col:
                vals   = df[col].values.astype(float)
                label  = vcfg.get("label", var_name)
                p_path = os.path.join(out_dir, preview_png)
                ok = _mpl_preview(x, y, z, vals, label, var_name,
                                  f"Particle shell — {label} (step {step:,})",
                                  p_path)
                if ok:
                    generated.append(p_path)
                    # 300-DPI report figure
                    rpt_stem = os.path.splitext(os.path.basename(preview_png))[0]
                    rpt_path = os.path.join(out_dir, "report_figures",
                                            rpt_stem + "_300dpi.png")
                    _mpl_preview(x, y, z, vals, label, var_name,
                                 f"Particle shell — {label} (step {step:,})",
                                 rpt_path, dpi=300)
                    generated.append(rpt_path)
                    if verbose:
                        print(f"  [OK] {os.path.relpath(p_path)}")

    # ── Shared animation preview PNG (temperature) ────────────────────────
    t_col = get_column(df, "T_p")
    if t_col:
        t_vals  = df[t_col].values.astype(float)
        anim_p  = os.path.join(out_dir, "animations",
                               "particle_animation_preview.png")
        ok = _mpl_preview(x, y, z, t_vals, "Temperature T\u209A", "T_p",
                          f"Particle shell — Temperature (step {step:,})",
                          anim_p)
        if ok:
            generated.append(anim_p)
            if verbose:
                print(f"  [OK] {os.path.relpath(anim_p)}")

    return generated
