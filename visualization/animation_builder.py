"""
animation_builder.py — Stage UI-4.1
==========================================================
Generates professional interactive particle animations:

  • Plotly HTML animations with custom controls (Play/Pause/
    Restart/Speed), stable title, step/phase display, and
    phase timeline — matching the static viewer design.
  • GIF preview and PNG thumbnail via particle_preview_builder (x-z projection).

All pages use the professional layout from plotly_3d_style.py.

Source files: particle_spherical_step_*.csv (preferred)
              particles_step_*.csv           (fallback)

The builder targets ~60 HTML frames, ~30 GIF frames.
Particles downsampled to --max-particles.
Planet reference is a static trace (not duplicated per frame).
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
    find_step_files, downsample_dataframe,
    extract_step_from_filename,
)
from plot_particles_3d import _load_particle_xyz, _infer_radii
from plotly_3d_style import (
    VARIABLE_CONFIG, ANIMATION_MODES, BASE_FRAME_MS, PHASE_CONFIG,
    DEFAULT_INNER_RADIUS, DEFAULT_OUTER_RADIUS,
    get_color_config, get_marker_size,
    get_scene_style, get_camera,
    build_planet_traces,
    write_animation_page,
)


# ──────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────

MAX_FRAMES_HTML = 60
MAX_FRAMES_GIF  = 30
MIN_FRAMES_WARN = 5


# ──────────────────────────────────────────────────────────────────────────
# Frame helpers
# ──────────────────────────────────────────────────────────────────────────

def _select_frames(files: List[str], max_frames: int) -> List[str]:
    """Evenly sub-select up to max_frames from a sorted file list."""
    n = len(files)
    if n <= max_frames:
        return files
    indices = np.linspace(0, n - 1, max_frames, dtype=int)
    return [files[i] for i in indices]


def _load_frame(path: str, max_particles: int
                ) -> Tuple[Optional[pd.DataFrame], Optional[int]]:
    """Load and downsample one frame CSV. Returns (df, step) or (None, None)."""
    df = read_csv_safe(path)
    if df is None:
        return None, None
    df   = normalize_columns(df)
    df   = downsample_dataframe(df, max_particles)
    step = extract_step_from_filename(path)
    return df, step


# ──────────────────────────────────────────────────────────────────────────
# Plotly animation builder
# ──────────────────────────────────────────────────────────────────────────

def _build_plotly_animation(
    files: List[str],
    var_name: str,
    max_particles: int,
    inner_r: float,
    outer_r: float,
) -> Optional[go.Figure]:
    """Build a Plotly Figure with animation frames.

    Trace layout:
      Index 0: particle scatter (updated each frame)
      Index 1+: planet/shell reference surfaces (static — not in frames)
    """
    vcfg       = VARIABLE_CONFIG.get(var_name, {})
    cb_title   = vcfg.get("label", var_name) + "<br>" + vcfg.get("units", "")

    # ── Collect all frames to determine global color range ────────────────
    frames_data = []
    all_vals    = []
    for fpath in files:
        df, step = _load_frame(fpath, max_particles)
        if df is None or step is None:
            continue
        xyz = _load_particle_xyz(df)
        if xyz is None:
            continue
        col = get_column(df, var_name)
        vals = df[col].values.astype(float) if col else np.zeros(len(xyz[0]))
        frames_data.append((xyz[0], xyz[1], xyz[2], vals, step))
        all_vals.append(vals)

    if not frames_data:
        return None

    all_vals_flat   = np.concatenate(all_vals)
    colorscale, cmin, cmax = get_color_config(var_name, all_vals_flat)
    x0, y0, z0, v0, step0 = frames_data[0]
    n_particles            = len(x0)
    msize                  = get_marker_size(n_particles)

    def _marker(v: np.ndarray) -> dict:
        return dict(
            size=msize,
            color=v,
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
        )

    # ── Initial particle trace ────────────────────────────────────────────
    init_trace = go.Scatter3d(
        x=x0, y=y0, z=z0,
        mode="markers",
        marker=_marker(v0),
        name="Particles",
        showlegend=False,
        hovertemplate="x:%{x:.3f} y:%{y:.3f} z:%{z:.3f}<extra></extra>",
    )

    # Planet reference traces (static — kept outside frames)
    planet_traces = build_planet_traces(inner_r, outer_r)

    # ── Animation frames (only update trace 0) ───────────────────────────
    step_labels = [str(s) for _, _, _, _, s in frames_data]
    anim_frames = [
        go.Frame(
            data=[go.Scatter3d(
                x=x, y=y, z=z,
                mode="markers",
                marker=_marker(vals),
            )],
            traces=[0],          # only update the particle trace
            name=str(step),
        )
        for x, y, z, vals, step in frames_data
    ]

    # ── Plotly slider (timeline visualization; controls removed) ──────────
    slider = dict(
        active=0,
        steps=[dict(
            args=[[label], {"frame":      {"duration": 0, "redraw": True},
                            "mode":       "immediate",
                            "transition": {"duration": 0}}],
            label=label,
            method="animate",
        ) for label in step_labels],
        x=0.0, y=-0.02, len=1.0,
        pad=dict(b=0, t=0),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#CBD5E1",
        borderwidth=1,
        currentvalue=dict(visible=False),   # hidden — shown in our custom strip
        font=dict(color="#0F172A", size=10),
        transition=dict(duration=0),
    )

    scene  = get_scene_style(outer_r)
    camera = get_camera()
    scene["camera"] = camera

    fig = go.Figure(
        data=[init_trace] + planet_traces,
        frames=anim_frames,
        layout=go.Layout(
            # Stable title — step is shown in the custom metadata strip
            title=dict(
                text=vcfg.get("subtitle", vcfg.get("label", var_name)),
                font=dict(size=16, color="#0F172A",
                          family="Inter, Roboto, system-ui, sans-serif"),
                x=0.5,
                xanchor="center",
            ),
            scene=scene,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#0F172A",
                      family="Inter, Roboto, system-ui, sans-serif"),
            height=700,
            margin=dict(l=0, r=0, t=42, b=40),
            showlegend=False,
            # No Plotly updatemenus — our custom controls handle play/pause
            updatemenus=[],
            sliders=[slider],
        ),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────
# Main public function
# ──────────────────────────────────────────────────────────────────────────

def build_particle_animations(
    input_dir: str,
    out_dir: str,
    max_particles: int = 2000,
    skip_animation: bool = False,
    verbose: bool = False,
) -> List[str]:
    """Build professional Plotly animation HTML files and GIF preview.

    Returns list of generated file paths.
    """
    generated: List[str] = []

    if skip_animation:
        print("  [SKIP] --skip-animation flag set — skipping animations.")
        return generated

    # ── Find all particle snapshot files ─────────────────────────────────
    files = find_step_files(input_dir, "particle_spherical_step_*.csv")
    if not files:
        files = find_step_files(input_dir, "particles_step_*.csv")
    if not files:
        print("  [WARN] No particle snapshot files found — skipping animations.")
        return generated

    n_files = len(files)
    if n_files < MIN_FRAMES_WARN:
        print(f"  [WARN] Only {n_files} snapshot file(s) — animation may be sparse.")

    html_files = _select_frames(files, MAX_FRAMES_HTML)

    if verbose:
        print(f"  [ANIM] {len(html_files)} HTML frames.")

    # ── Infer shell geometry from first file ──────────────────────────────
    df0, _ = _load_frame(html_files[0], max_particles)
    if df0 is not None:
        inner_r, outer_r = _infer_radii(df0)
    else:
        inner_r, outer_r = DEFAULT_INNER_RADIUS, DEFAULT_OUTER_RADIUS

    first_step = extract_step_from_filename(html_files[0])  or 0
    last_step  = extract_step_from_filename(html_files[-1]) or 100_000

    # ── HTML animations ───────────────────────────────────────────────────
    modes = [
        ("T_p",  "particle_animation_temperature"),
        ("q_p",  "particle_animation_qp"),
        ("v_r",  "particle_animation_vr"),
    ]

    for var_name, stem in modes:
        # Check column exists in first file
        if df0 is None or get_column(df0, var_name) is None:
            if verbose:
                print(f"  [INFO] Column '{var_name}' missing — skipping {stem}.")
            continue

        pfig = _build_plotly_animation(
            html_files, var_name, max_particles, inner_r, outer_r
        )
        if pfig is None:
            print(f"  [WARN] No animation data built for {stem}.")
            continue

        frame_names = [str(extract_step_from_filename(f) or i)
                       for i, f in enumerate(html_files)]

        html_path = os.path.join(out_dir, "html", f"{stem}.html")
        try:
            write_animation_page(
                fig=pfig,
                out_path=html_path,
                var_name=var_name,
                frame_names=frame_names,
                first_step=first_step,
                last_step=last_step,
                n_particles=max_particles,
                inner_r=inner_r,
                outer_r=outer_r,
                base_ms=BASE_FRAME_MS,
            )
            generated.append(html_path)
            if verbose:
                print(f"  [OK] {os.path.relpath(html_path)}")
        except Exception as exc:
            print(f"  [ERROR] Writing {stem}.html failed: {exc}")

    # ── GIF preview (temperature, x-z projection) ─────────────────────────
    from particle_preview_builder import save_particle_preview_gif
    gif_files_out = save_particle_preview_gif(
        input_dir, out_dir,
        var_name="T_p",
        max_particles=min(max_particles, 3000),
        max_frames=MAX_FRAMES_GIF,
        verbose=verbose,
    )
    generated.extend(gif_files_out)

    return generated
