"""
particle_preview_builder.py — Stage UI-4.2 (focused)
==========================================================
Generates ONLY these outputs:

  png/particle_preview_temperature.png
  png/particle_preview_vr.png
  report_figures/particle_preview_temperature_300dpi.png
  report_figures/particle_preview_vr_300dpi.png
  animations/particle_animation_preview.gif
  animations/particle_animation_preview.png

Shared x–z projection styling for static PNGs and GIF frames.
==========================================================
"""

from __future__ import annotations

import io
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from data_loader import (
    read_csv_safe,
    normalize_columns,
    get_column,
    find_latest_file,
    find_step_files,
    extract_step_from_filename,
    set_mpl_style,
)
from plot_particles_3d import _load_particle_xyz
from plotly_3d_style import DEFAULT_INNER_RADIUS, DEFAULT_OUTER_RADIUS, get_color_config

# ── Layout ────────────────────────────────────────────────────────────────
PREVIEW_W_IN = 12.0
PREVIEW_H_IN = 9.0
PREVIEW_DPI  = 100
REPORT_DPI   = 300
BG_COLOR     = "#F8FAFC"
PLOT_RECT    = [0.04, 0.11, 0.86, 0.76]
CBAR_RECT    = [0.912, 0.11, 0.018, 0.76]
SEED         = 42
MAX_GIF_FRAMES = 30
SHELL_PADDING  = 0.05

# Only the two static previews requested in this task
STATIC_VARS = ("T_p", "v_r")

VARIABLE_PREVIEW: Dict[str, Dict[str, str]] = {
    "T_p": {
        "stem": "temperature",
        "main_title": "Atmospheric Particle Shell — Temperature T_p",
        "subtitle": "Step {step:,} · 2D x-z projection of the 3D atmospheric shell",
        "gif_subtitle": "2D x-z projection of the 3D atmospheric shell",
        "cbar_label": "Temperature T_p\n[model units]",
        "cmap": "turbo",
    },
    "v_r": {
        "stem": "vr",
        "main_title": "Atmospheric Particle Shell — Radial Velocity v_r",
        "subtitle": "Step {step:,} · Red: outward motion · Blue: inward motion",
        "gif_subtitle": "Red: outward motion · Blue: inward motion",
        "cbar_label": "Radial velocity v_r\n[model units]",
        "cmap": "RdBu_r",
    },
}


def _particle_id_column(df) -> Optional[str]:
    for name in ("particle_id", "id", "pid", "particle_ID"):
        if name in df.columns:
            return name
    lower = {c.lower(): c for c in df.columns}
    for name in ("particle_id", "id", "pid"):
        if name in lower:
            return lower[name]
    return None


def select_consistent_particles(
    df,
    max_particles: int,
    seed: int = SEED,
) -> Tuple[Any, Optional[str], bool]:
    id_col = _particle_id_column(df)
    if id_col is not None:
        ids = np.sort(df[id_col].dropna().unique())
        if len(ids) > max_particles:
            rng = np.random.default_rng(seed)
            chosen = np.sort(rng.choice(ids, size=max_particles, replace=False))
        else:
            chosen = ids
        return chosen, id_col, True
    n = min(len(df), max_particles)
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(df), size=n, replace=False))
    return indices, None, False


def _subset_dataframe(df, selection, id_col: Optional[str], use_ids: bool):
    if use_ids and id_col:
        return df[df[id_col].isin(selection)].sort_values(id_col).reset_index(drop=True)
    return df.iloc[selection].reset_index(drop=True)


def model_shell_radii() -> Tuple[float, float]:
    """Use model geometry R=50, outer R+H=70."""
    return DEFAULT_INNER_RADIUS, DEFAULT_OUTER_RADIUS


def compute_xz_limits(
    inner_r: float = DEFAULT_INNER_RADIUS,
    outer_r: float = DEFAULT_OUTER_RADIUS,
    padding: float = SHELL_PADDING,
) -> Tuple[float, float]:
    lim = float(outer_r) * (1.0 + padding)
    return -lim, lim


def compute_color_limits(var_name: str, values: np.ndarray) -> Tuple[str, float, float]:
    _, cmin, cmax = get_color_config(var_name, values)
    cfg = VARIABLE_PREVIEW.get(var_name, {})
    return cfg.get("cmap", "viridis"), cmin, cmax


def mpl_marker_size(n: int) -> float:
    if n <= 2_000:
        return 8.0
    if n <= 5_000:
        return 5.5
    return 3.5


def _draw_shell_circles(ax, inner_r: float, outer_r: float) -> None:
    ax.add_patch(Circle((0, 0), inner_r, fill=False, edgecolor="#64748B",
                          linewidth=1.0, alpha=0.28, zorder=1))
    ax.add_patch(Circle((0, 0), outer_r, fill=False, edgecolor="#94A3B8",
                          linewidth=1.0, alpha=0.20, linestyle="--", zorder=1))


def render_particle_preview_frame(
    x: np.ndarray,
    z: np.ndarray,
    values: np.ndarray,
    var_name: str,
    step: int,
    *,
    vmin: float,
    vmax: float,
    cmap: str,
    xlim: Tuple[float, float],
    inner_r: float,
    outer_r: float,
    marker_size: Optional[float] = None,
    show_titles: bool = True,
    show_step_label: bool = False,
    fixed_subtitle: Optional[str] = None,
    return_array: bool = False,
) -> Any:
    cfg = VARIABLE_PREVIEW.get(var_name, {})
    px = x.astype(float)
    pz = z.astype(float)
    n = len(px)
    msize = marker_size if marker_size is not None else mpl_marker_size(n)

    set_mpl_style()
    fig = plt.figure(figsize=(PREVIEW_W_IN, PREVIEW_H_IN), facecolor=BG_COLOR)
    ax = fig.add_axes(PLOT_RECT, facecolor=BG_COLOR)
    cax = fig.add_axes(CBAR_RECT, facecolor=BG_COLOR)

    _draw_shell_circles(ax, inner_r, outer_r)
    sc = ax.scatter(
        px, pz, c=values, cmap=cmap, vmin=vmin, vmax=vmax,
        s=msize, alpha=0.88, linewidths=0, rasterized=True, zorder=3,
    )
    ax.set_xlim(xlim)
    ax.set_ylim(xlim)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    cb = fig.colorbar(sc, cax=cax)
    cb.ax.tick_params(labelsize=8, colors="#1E293B")
    cb.set_label(cfg.get("cbar_label", var_name), fontsize=9, color="#1E293B", labelpad=4)

    if show_titles:
        fig.suptitle(cfg.get("main_title", ""), fontsize=14, fontweight="bold",
                     color="#0F172A", y=0.97)
        sub = fixed_subtitle if fixed_subtitle is not None else cfg.get("subtitle", "").format(step=step)
        ax.set_title(sub, fontsize=10, color="#64748B", pad=8)

    if show_step_label:
        ax.text(
            0.03, 0.97, f"Step {step:,}",
            transform=ax.transAxes, fontsize=14, fontweight="bold", color="#0F172A",
            va="top", ha="left", zorder=5,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#CBD5E1", alpha=0.93),
        )

    if return_array:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=PREVIEW_DPI, facecolor=BG_COLOR, edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        try:
            import imageio.v2 as imageio
        except ImportError:
            import imageio  # type: ignore
        return imageio.imread(buf)
    return fig


def _save_figure(fig, path: str, dpi: int) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)


def generate_static_previews(
    input_dir: str,
    out_dir: str,
    max_particles: int = 5000,
    verbose: bool = False,
) -> List[str]:
    """Generate particle_preview_temperature.png and particle_preview_vr.png (+ 300 DPI)."""
    generated: List[str] = []

    latest = find_latest_file(input_dir, "particle_spherical_step_*.csv")
    if latest is None:
        latest = find_latest_file(input_dir, "particles_step_*.csv")
    if latest is None:
        print("  [WARN] No particle snapshot — skipping static previews.")
        return generated

    step = extract_step_from_filename(latest) or 0
    if verbose:
        print(f"  [PREVIEW] Source CSV: {os.path.relpath(latest)}")
        print(f"  [PREVIEW] Latest step: {step:,}")
        print(f"  [PREVIEW] Projection: x-z (equal aspect)")

    df = read_csv_safe(latest)
    if df is None:
        return generated
    df = normalize_columns(df)

    xyz = _load_particle_xyz(df)
    if xyz is None:
        print("  [WARN] No position columns — skipping static previews.")
        return generated

    inner_r, outer_r = model_shell_radii()
    xlim = compute_xz_limits(inner_r, outer_r)

    sel, id_col, use_ids = select_consistent_particles(df, max_particles)
    sub = _subset_dataframe(df, sel, id_col, use_ids)
    xyz_sub = _load_particle_xyz(sub)
    if xyz_sub is None:
        print("  [WARN] Could not project subset — skipping static previews.")
        return generated
    sx, _sy, sz = xyz_sub
    msize = mpl_marker_size(len(sub))

    if verbose:
        print(f"  [PREVIEW] Displayed particles: {len(sub):,}")
        print(f"  [PREVIEW] Stable particle IDs: {use_ids}")
        print(f"  [PREVIEW] Marker size: {msize}")
        print(f"  [PREVIEW] x/z limits: [{xlim[0]:.1f}, {xlim[1]:.1f}]")
        print(f"  [PREVIEW] Shell radii: inner={inner_r:.0f}, outer={outer_r:.0f}")

    for var_name in STATIC_VARS:
        cfg = VARIABLE_PREVIEW[var_name]
        col = get_column(sub, var_name)
        if col is None:
            if verbose:
                print(f"  [SKIP] {var_name}: column missing")
            continue

        vals = sub[col].values.astype(float)
        cmap, vmin, vmax = compute_color_limits(var_name, vals)
        if verbose:
            if var_name == "v_r":
                print(f"  [PREVIEW] v_r symmetric limit: ±{max(abs(vmin), abs(vmax)):.6g}")
            else:
                print(f"  [PREVIEW] {var_name} color limits: [{vmin:.6g}, {vmax:.6g}]")

        png_path = os.path.join(out_dir, "png", f"particle_preview_{cfg['stem']}.png")
        rpt_path = os.path.join(out_dir, "report_figures",
                                f"particle_preview_{cfg['stem']}_300dpi.png")

        fig = render_particle_preview_frame(
            sx, sz, vals, var_name, step,
            vmin=vmin, vmax=vmax, cmap=cmap, xlim=xlim,
            inner_r=inner_r, outer_r=outer_r, marker_size=msize,
        )
        _save_figure(fig, png_path, PREVIEW_DPI)
        generated.append(png_path)

        fig2 = render_particle_preview_frame(
            sx, sz, vals, var_name, step,
            vmin=vmin, vmax=vmax, cmap=cmap, xlim=xlim,
            inner_r=inner_r, outer_r=outer_r, marker_size=msize,
        )
        _save_figure(fig2, rpt_path, REPORT_DPI)
        generated.append(rpt_path)

        if verbose:
            print(f"  [OK] {os.path.relpath(png_path)}")
            print(f"  [OK] {os.path.relpath(rpt_path)}")

    return generated


def _select_gif_frames(files: List[str], max_frames: int) -> List[str]:
    if len(files) <= max_frames:
        return files
    idx = np.linspace(0, len(files) - 1, max_frames, dtype=int)
    return [files[i] for i in idx]


def save_particle_preview_gif(
    input_dir: str,
    out_dir: str,
    var_name: str = "T_p",
    max_particles: int = 3000,
    max_frames: int = MAX_GIF_FRAMES,
    verbose: bool = False,
) -> List[str]:
    """Build particle_animation_preview.gif and .png (temperature, x-z projection)."""
    generated: List[str] = []

    files = find_step_files(input_dir, "particle_spherical_step_*.csv")
    if not files:
        files = find_step_files(input_dir, "particles_step_*.csv")
    if not files:
        print("  [WARN] No snapshot files — skipping GIF preview.")
        return generated

    gif_files = _select_gif_frames(files, max_frames)
    if verbose:
        print(f"  [GIF] Snapshot files used: {len(gif_files)} (from {len(files)} available)")
        print(f"  [GIF] Projection: x-z (fixed limits, fixed marker size)")

    df0 = read_csv_safe(gif_files[0])
    if df0 is None:
        return generated
    df0 = normalize_columns(df0)
    sel, id_col, use_ids = select_consistent_particles(df0, max_particles)

    inner_r, outer_r = model_shell_radii()
    xlim = compute_xz_limits(inner_r, outer_r)
    cfg = VARIABLE_PREVIEW[var_name]

    all_vals: List[float] = []
    frame_data: List[Tuple[int, np.ndarray, np.ndarray, np.ndarray]] = []

    for fpath in gif_files:
        df = read_csv_safe(fpath)
        if df is None:
            continue
        df = normalize_columns(df)
        step = extract_step_from_filename(fpath) or 0
        sub = _subset_dataframe(df, sel, id_col, use_ids)
        xyz = _load_particle_xyz(sub)
        if xyz is None:
            continue
        fx, _fy, fz = xyz
        col = get_column(sub, var_name)
        if col is None:
            continue
        vals = sub[col].values.astype(float)
        all_vals.extend(vals[np.isfinite(vals)].tolist())
        frame_data.append((step, fx, fz, vals))

    if not frame_data:
        print("  [WARN] No usable GIF frame data.")
        return generated

    _, vmin, vmax = compute_color_limits(var_name, np.array(all_vals, dtype=float))
    cmap = cfg["cmap"]
    msize = mpl_marker_size(len(frame_data[0][3]))
    gif_subtitle = cfg.get("gif_subtitle", "")

    if verbose:
        print(f"  [GIF] Displayed particles: {len(frame_data[0][3]):,}")
        print(f"  [GIF] Stable particle IDs: {use_ids}")
        print(f"  [GIF] Marker size: {msize}")
        print(f"  [GIF] x/z limits: [{xlim[0]:.1f}, {xlim[1]:.1f}]")
        print(f"  [GIF] Global temperature limits: [{vmin:.6g}, {vmax:.6g}]")

    frames_rgb = []
    for step, fx, fz, vals in frame_data:
        arr = render_particle_preview_frame(
            fx, fz, vals, var_name, step,
            vmin=vmin, vmax=vmax, cmap=cmap, xlim=xlim,
            inner_r=inner_r, outer_r=outer_r, marker_size=msize,
            show_titles=True, show_step_label=True,
            fixed_subtitle=gif_subtitle,
            return_array=True,
        )
        frames_rgb.append(arr)

    n_frames = len(frames_rgb)
    duration_ms = int(max(300, min(450, 13500 // max(n_frames, 1))))

    gif_path = os.path.join(out_dir, "animations", "particle_animation_preview.gif")
    png_path = os.path.join(out_dir, "animations", "particle_animation_preview.png")

    try:
        import imageio.v2 as imageio
    except ImportError:
        try:
            import imageio  # type: ignore
        except ImportError:
            print("  [WARN] imageio not installed — skipping GIF.")
            return generated

    os.makedirs(os.path.dirname(gif_path), exist_ok=True)
    imageio.mimsave(gif_path, frames_rgb, duration=duration_ms / 1000.0, loop=0)
    generated.append(gif_path)

    last_step, lx, lz, lvals = frame_data[-1]
    fig = render_particle_preview_frame(
        lx, lz, lvals, var_name, last_step,
        vmin=vmin, vmax=vmax, cmap=cmap, xlim=xlim,
        inner_r=inner_r, outer_r=outer_r, marker_size=msize,
        show_step_label=True,
        fixed_subtitle=gif_subtitle,
    )
    _save_figure(fig, png_path, PREVIEW_DPI)
    generated.append(png_path)

    if verbose:
        print(f"  [GIF] Duration per frame: {duration_ms} ms")
        print(f"  [OK] {os.path.relpath(gif_path)} ({os.path.getsize(gif_path) / 1024:.0f} kB)")
        print(f"  [OK] {os.path.relpath(png_path)}")

    return generated
