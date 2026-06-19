"""
plotly_3d_style.py — Stage UI-4.1
===========================================================
Shared styling, color configuration, planet-reference
geometry, and professional HTML page generation for both:
  • plot_particles_3d.py  (static viewers)
  • animation_builder.py  (animated viewers)

All generated pages match the dashboard visual theme:
  light background, dark navy header, system typography,
  consistent Turbo/YlGnBu/RdBu_r color scales.
===========================================================
"""

from __future__ import annotations
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Optional heavy imports (handled gracefully) ────────────────────────────
try:
    import plotly.graph_objects as go
    import plotly.io as pio
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False


# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────

# Simulation phase boundaries (step numbers)
PHASE_CONFIG = {
    "stage1_end":     20_000,
    "stage2_end":     40_000,
    "stage3_end":     60_000,
    "moisture_start": 60_000,
}

# Default planet geometry (model units)
DEFAULT_INNER_RADIUS = 50.0
DEFAULT_OUTER_RADIUS = 70.0

# Per-variable display config
VARIABLE_CONFIG: Dict[str, Dict[str, Any]] = {
    "T_p": {
        "label":     "Particle temperature T_p",
        "units":     "[model units]",
        "colorscale":"Turbo",
        "diverging": False,
        "page_title":"3D Atmospheric Particle Viewer",
        "subtitle":  "Colored by: Particle Temperature T\u209A",
        "stem":      "temperature",
        "col_key":   "T_p",
    },
    "v_r": {
        "label":     "Radial velocity v_r",
        "units":     "[model units]",
        "colorscale":"RdBu_r",
        "diverging": True,
        "page_title":"3D Atmospheric Particle Viewer",
        "subtitle":  "Colored by: Radial Velocity v\u1D63 (red\u2191 blue\u2193)",
        "stem":      "radial vel.",
        "col_key":   "v_r",
    },
    "v_theta": {
        "label":     "Meridional velocity v\u03B8",
        "units":     "[model units]",
        "colorscale":"RdBu_r",
        "diverging": True,
        "page_title":"3D Atmospheric Particle Viewer",
        "subtitle":  "Colored by: Meridional Velocity v\u03B8",
        "stem":      "meridional vel.",
        "col_key":   "v_theta",
    },
    "q_p": {
        "label":     "Specific humidity q\u209A",
        "units":     "",
        "colorscale":"YlGnBu",
        "diverging": False,
        "page_title":"3D Atmospheric Particle Viewer",
        "subtitle":  "Colored by: Specific Humidity q\u209A",
        "stem":      "humidity",
        "col_key":   "q_p",
    },
}

# Viewer mode navigation definitions
VIEWER_MODES = [
    ("Temperature",      "particle_3d_temperature.html"),
    ("Radial vel.",      "particle_3d_vr.html"),
    ("Meridional vel.",  "particle_3d_vtheta.html"),
    ("Humidity q\u209A", "particle_3d_qp.html"),
]

ANIMATION_MODES = [
    ("Temperature",      "particle_animation_temperature.html"),
    ("Radial vel.",      "particle_animation_vr.html"),
    ("Humidity q\u209A", "particle_animation_qp.html"),
]

# Animation playback timing (ms)
BASE_FRAME_MS = 450


# ──────────────────────────────────────────────────────────────────────────
# Color configuration
# ──────────────────────────────────────────────────────────────────────────

def get_color_config(
    var_name: str,
    values: np.ndarray,
) -> Tuple[str, float, float]:
    """Return (colorscale, cmin, cmax) for a variable with percentile-based limits.

    Uses 2nd–98th percentile to reduce outlier influence.
    For diverging variables: symmetric range around zero.
    Falls back to finite min/max or a small epsilon range if needed.
    """
    cfg = VARIABLE_CONFIG.get(var_name, {})
    colorscale = cfg.get("colorscale", "Turbo")
    diverging  = cfg.get("diverging", False)

    finite = values[np.isfinite(values)] if len(values) else np.array([])
    if len(finite) == 0:
        return colorscale, 0.0, 1.0

    if diverging:
        abs_p98 = float(np.percentile(np.abs(finite), 98))
        if abs_p98 < 1e-12:
            abs_p98 = float(max(abs(finite.min()), abs(finite.max())))
        if abs_p98 < 1e-12:
            abs_p98 = 1e-6
        return colorscale, -abs_p98, abs_p98
    else:
        p2  = float(np.percentile(finite, 2))
        p98 = float(np.percentile(finite, 98))
        if abs(p98 - p2) < 1e-12:
            p2  = float(finite.min())
            p98 = float(finite.max())
        if abs(p98 - p2) < 1e-12:
            p98 = p2 + 1e-6
        # q_p must be non-negative
        if var_name == "q_p":
            p2 = max(0.0, p2)
        return colorscale, p2, p98


def get_marker_size(n_particles: int) -> float:
    """Dynamic marker size based on displayed particle count."""
    if n_particles <= 2_000:
        return 4.0
    if n_particles <= 5_000:
        return 3.0
    return 2.5


# ──────────────────────────────────────────────────────────────────────────
# Camera & scene styling
# ──────────────────────────────────────────────────────────────────────────

def get_camera() -> Dict[str, Any]:
    """Slightly elevated diagonal camera that shows the spherical shell well."""
    return dict(eye=dict(x=1.25, y=1.1, z=0.85),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1))


def get_scene_style(r_outer: float = DEFAULT_OUTER_RADIUS) -> Dict[str, Any]:
    """Light scientific 3D scene style. Axis ranges sized to fit the shell."""
    ax = dict(
        backgroundcolor="#F8FAFC",
        gridcolor="#CBD5E1",
        zerolinecolor="#94A3B8",
        zerolinewidth=1,
        tickfont=dict(color="#374151", size=10),
        title=dict(font=dict(color="#0F172A", size=11)),
    )
    lim = r_outer * 1.08
    return dict(
        bgcolor="#F8FAFC",
        xaxis=dict(**ax, range=[-lim, lim]),
        yaxis=dict(**ax, range=[-lim, lim]),
        zaxis=dict(**ax, range=[-lim, lim]),
        aspectmode="cube",
        camera=get_camera(),
    )


# ──────────────────────────────────────────────────────────────────────────
# Planet / shell reference geometry
# ──────────────────────────────────────────────────────────────────────────

def _sphere_mesh(radius: float, n: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parametric sphere at origin, resolution n×n."""
    phi   = np.linspace(0, 2 * np.pi, n + 1)
    theta = np.linspace(-np.pi / 2, np.pi / 2, n // 2 + 1)
    phi, theta = np.meshgrid(phi, theta)
    x = radius * np.cos(theta) * np.cos(phi)
    y = radius * np.cos(theta) * np.sin(phi)
    z = radius * np.sin(theta)
    return x, y, z


def build_planet_traces(
    inner_r: float = DEFAULT_INNER_RADIUS,
    outer_r: float = DEFAULT_OUTER_RADIUS,
) -> List[Any]:
    """Return a list of Plotly traces representing:
      1. Faint inner planet surface (semi-transparent gray sphere)
      2. Sparse outer-shell wireframe (latitude lines only)
    These traces are non-animated (static background).
    """
    if not _PLOTLY_OK:
        return []
    traces = []

    # ── Inner planet surface ──────────────────────────────────────────────
    xs, ys, zs = _sphere_mesh(inner_r, n=24)
    traces.append(go.Surface(
        x=xs, y=ys, z=zs,
        colorscale=[[0, "#94A3B8"], [1, "#94A3B8"]],
        showscale=False,
        opacity=0.13,
        hoverinfo="skip",
        lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0,
                      roughness=1.0, fresnel=0.0),
        name="Planet surface",
        showlegend=False,
    ))

    # ── Outer atmospheric shell wireframe (latitude lines) ────────────────
    for lat_deg in np.linspace(-75, 75, 7):
        phi    = np.linspace(0, 2 * np.pi, 60)
        r_circ = outer_r * np.cos(np.radians(lat_deg))
        z_val  = outer_r * np.sin(np.radians(lat_deg))
        traces.append(go.Scatter3d(
            x=r_circ * np.cos(phi),
            y=r_circ * np.sin(phi),
            z=np.full_like(phi, z_val),
            mode="lines",
            line=dict(color="#94A3B8", width=1),
            opacity=0.22,
            hoverinfo="skip",
            showlegend=False,
            name="Shell boundary",
        ))

    return traces


# ──────────────────────────────────────────────────────────────────────────
# Hover template
# ──────────────────────────────────────────────────────────────────────────

def build_hover_data(df: Any, var_col: str) -> Tuple[List[str], str]:
    """Build customdata array and hovertemplate for rich particle hovering.

    Returns (customdata_list_of_lists, hovertemplate_str).
    Works with any pandas DataFrame that has the particle columns.
    """
    import pandas as pd  # noqa

    optional_cols = [
        ("particle_id", "ID",        "{:.0f}"),
        ("radius",       "Radius",    "{:.3f}"),
        ("altitude",     "Alt.",      "{:.3f}"),
        ("latitude_deg", "Lat.",      "{:.2f}\u00b0"),
        ("longitude_deg","Lon.",      "{:.2f}\u00b0"),
        ("temperature",  "Temp.",     "{:.4f}"),
        ("q_p",          "q\u209A",   "{:.2e}"),
        ("v_r",          "v_r",       "{:.4f}"),
        ("v_theta",      "v\u03B8",   "{:.4f}"),
        ("v_phi_relative","v\u03C6",  "{:.4f}"),
    ]

    present = []
    for col, name, fmt in optional_cols:
        if col in df.columns:
            present.append((col, name, fmt))

    custom = [
        [row[col] for col, _, _ in present]
        for _, row in df.iterrows()
    ] if present else None

    lines = ["<b>x:</b> %{x:.3f}  y: %{y:.3f}  z: %{z:.3f}"]
    for i, (_, name, _) in enumerate(present):
        lines.append(f"<b>{name}:</b> %{{customdata[{i}]}}")

    template = "<br>".join(lines) + "<extra></extra>"
    return custom, template


# ──────────────────────────────────────────────────────────────────────────
# Phase naming
# ──────────────────────────────────────────────────────────────────────────

def get_phase_name(step: int, cfg: Optional[Dict] = None) -> str:
    """Return human-readable phase name for a simulation step."""
    c   = cfg or PHASE_CONFIG
    s1e = c.get("stage1_end",     20_000)
    s2e = c.get("stage2_end",     40_000)
    s3e = c.get("stage3_end",     60_000)
    ms  = c.get("moisture_start", 60_000)
    step = int(step)
    if step < s1e:
        return "Stage 1 \u2014 Hydrostatic spin-up"
    if step < s2e:
        return "Stage 2 \u2014 Thermal forcing"
    if step < s3e:
        return "Stage 3 \u2014 Rotation & circulation"
    if step >= ms:
        return "Stage 4 \u2014 Moisture physics active"
    return "Stage 4 \u2014 Moisture coupling"


# ──────────────────────────────────────────────────────────────────────────
# Inline CSS for all generated pages
# ──────────────────────────────────────────────────────────────────────────

def _page_css() -> str:
    return """
:root{
  --bg:#F4F7FB;--surface:#FFF;--border:#E2E8F0;
  --text:#0F172A;--muted:#64748B;--faint:#94A3B8;
  --hdr:#0D1B2A;--hdr-accent:#4FC3F7;
  --primary:#2563EB;--primary-h:#1D4ED8;
  --pass:#16A34A;--warn:#D97706;
  --radius:8px;--shadow:0 2px 10px rgba(26,37,64,.1);
  --trans:0.15s ease;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);
  font-family:Inter,Roboto,system-ui,-apple-system,sans-serif;
  color:var(--text);font-size:14px;line-height:1.5}
a{color:var(--primary);text-decoration:none}
a:hover{text-decoration:underline}

/* ── Header ── */
.vhdr{
  background:var(--hdr);color:#E8EDF5;
  padding:.55rem 1.2rem;
  display:flex;align-items:center;gap:1rem;
  flex-wrap:wrap;position:sticky;top:0;z-index:100;
  box-shadow:0 2px 8px rgba(0,0,0,.35);
}
.vhdr-brand{
  color:var(--hdr-accent);font-weight:700;font-size:.95rem;
  white-space:nowrap;text-decoration:none;letter-spacing:.01em;
}
.vhdr-brand:hover{opacity:.85;text-decoration:none}
.vhdr-titles{flex:1;min-width:160px}
.vhdr-title{font-size:1.05rem;font-weight:700;color:#FFF;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vhdr-sub{font-size:.78rem;color:var(--hdr-accent);margin-top:.1rem;
  font-weight:400}
.vhdr-meta{
  display:flex;flex-wrap:wrap;gap:.4rem .9rem;
  font-size:.75rem;color:#94AABF;
  flex-shrink:0;
}
.vmeta-item b{color:#C5D8E8}

/* ── Mode navigation ── */
.mode-nav{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:.5rem 1.2rem;display:flex;align-items:center;gap:.5rem;
  flex-wrap:wrap;
}
.mode-nav-label{font-size:.72rem;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;margin-right:.25rem}
.mnav-btn{
  padding:.28rem .7rem;border-radius:20px;font-size:.78rem;
  font-weight:600;border:1.5px solid var(--border);
  background:transparent;color:var(--muted);cursor:pointer;
  text-decoration:none;transition:all var(--trans);white-space:nowrap;
}
.mnav-btn:hover{border-color:var(--primary);color:var(--primary);
  text-decoration:none}
.mnav-btn.active{background:var(--primary);border-color:var(--primary);
  color:#FFF}
.mnav-sep{
  width:1px;height:16px;background:var(--border);margin:0 .3rem;
  flex-shrink:0;align-self:center;
}

/* ── Plot outer wrapper ── */
.plot-outer{
  position:relative;background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  margin:.75rem 1rem;
  box-shadow:var(--shadow);
  overflow:hidden;
}
.plot-outer.is-fullscreen{
  position:fixed!important;inset:0!important;margin:0!important;
  border-radius:0!important;z-index:9999;
}

/* ── Toolbar ── */
.toolbar{
  display:flex;align-items:center;gap:.4rem;
  padding:.45rem .75rem;background:var(--bg);
  border-bottom:1px solid var(--border);
  flex-wrap:wrap;
}
.tbtn{
  padding:.3rem .7rem;border-radius:6px;font-size:.78rem;
  font-weight:600;border:1.5px solid var(--border);
  background:var(--surface);color:var(--text);cursor:pointer;
  transition:all var(--trans);white-space:nowrap;
}
.tbtn:hover{background:var(--primary);border-color:var(--primary);
  color:#FFF}
.tbtn.active{background:var(--primary);border-color:var(--primary);
  color:#FFF}
.tbtn-sep{
  width:1px;height:18px;background:var(--border);margin:0 .1rem;
  flex-shrink:0;
}

/* ── The Plotly div itself ── */
.js-plotly-plot,.plotly-graph-div{width:100%!important}
#plot-div{width:100%;height:78vh;min-height:420px}

/* ── Animation controls ── */
.anim-bar{
  padding:.5rem .75rem .4rem;border-bottom:1px solid var(--border);
  background:var(--surface);display:flex;flex-wrap:wrap;
  align-items:center;gap:.5rem .6rem;
}
.anim-group{display:flex;align-items:center;gap:.3rem;flex-wrap:wrap}
.anim-label{font-size:.7rem;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;margin-right:.1rem}
.abtn{
  padding:.32rem .72rem;border-radius:6px;font-size:.8rem;
  font-weight:600;border:1.5px solid var(--border);
  background:var(--surface);color:var(--text);cursor:pointer;
  transition:all var(--trans);white-space:nowrap;min-width:2.2rem;
  text-align:center;
}
.abtn:hover{background:var(--primary);border-color:var(--primary);color:#FFF}
.abtn.active{background:var(--primary);border-color:var(--primary);color:#FFF}
.spd-btn{font-size:.75rem;padding:.28rem .55rem}

/* ── Step / phase display (animation) ── */
.step-display{
  display:flex;flex-wrap:wrap;gap:.3rem 1rem;padding:.4rem .8rem;
  background:rgba(244,247,251,.75);border-bottom:1px solid var(--border);
  font-size:.8rem;
}
.sditem b{color:var(--text)}
.sditem span{color:var(--muted)}

/* ── Phase timeline ── */
.phase-timeline{
  padding:.55rem .8rem .4rem;background:var(--bg);
  border-bottom:1px solid var(--border);
}
.pt-header{font-size:.68rem;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;margin-bottom:.35rem}
.pt-track{
  position:relative;height:20px;
  background:linear-gradient(to right,var(--border),var(--border));
  background-size:100% 2px;background-repeat:no-repeat;
  background-position:center;
}
.pt-marker{position:absolute;top:0;transform:translateX(-50%)}
.pt-tick{
  width:2px;height:10px;border-radius:1px;margin:0 auto;
}
.pt-tick.s1{background:#94A3B8}
.pt-tick.s2{background:#60A5FA}
.pt-tick.s3{background:#A78BFA}
.pt-tick.s4{background:#34D399}
.pt-mlabel{
  font-size:.62rem;color:var(--muted);white-space:nowrap;
  margin-top:1px;text-align:center;line-height:1.2;
}
.pt-progress{
  position:absolute;left:0;top:50%;height:3px;border-radius:2px;
  background:var(--primary);transform:translateY(-50%);
  transition:width .2s ease;pointer-events:none;
  width:0%;
}

/* ── Footer ── */
.vfooter{
  background:var(--hdr);color:#64788F;
  padding:.7rem 1.2rem;display:flex;flex-wrap:wrap;
  gap:.3rem 1.5rem;align-items:center;font-size:.75rem;
}
.vfooter a{color:#4FC3F7;font-weight:500}

/* ── Responsive ── */
@media(max-width:640px){
  #plot-div{height:60vh}
  .vhdr-meta{display:none}
  .phase-timeline{display:none}
}
"""


# ──────────────────────────────────────────────────────────────────────────
# Base JavaScript (viewer & animation-common)
# ──────────────────────────────────────────────────────────────────────────

def _base_viewer_js(camera: Dict, title: str) -> str:
    cam_j = json.dumps(camera)
    return f"""
var _CAMERA = {cam_j};
// _VIEWER_GD is set by Plotly's post_script (runs during page load);
// the DOMContentLoaded fallback handles any edge cases.
var _PLOT_GD = window._VIEWER_GD || null;
document.addEventListener('DOMContentLoaded', function() {{
  if (!_PLOT_GD) {{
    _PLOT_GD = window._VIEWER_GD
               || document.querySelector('.js-plotly-plot')
               || document.querySelector('.plotly-graph-div');
  }}
}});

function resetCamera() {{
  if (_PLOT_GD) Plotly.relayout(_PLOT_GD, {{'scene.camera': _CAMERA}});
}}

function toggleFullscreen() {{
  var wrap = document.getElementById('viewer-wrap');
  if (!document.fullscreenElement) {{
    (wrap.requestFullscreen ? wrap.requestFullscreen()
       : wrap.webkitRequestFullscreen ? wrap.webkitRequestFullscreen()
       : Promise.resolve()).then(function() {{
      wrap.classList.add('is-fullscreen');
      setTimeout(function() {{
        if (_PLOT_GD) Plotly.Plots.resize(_PLOT_GD);
      }}, 120);
    }}).catch(function(){{}});
  }} else {{
    (document.exitFullscreen ? document.exitFullscreen()
       : document.webkitExitFullscreen ? document.webkitExitFullscreen()
       : Promise.resolve());
  }}
}}
document.addEventListener('fullscreenchange', function() {{
  var wrap = document.getElementById('viewer-wrap');
  if (!document.fullscreenElement) wrap.classList.remove('is-fullscreen');
  setTimeout(function() {{
    if (_PLOT_GD) Plotly.Plots.resize(_PLOT_GD);
  }}, 120);
}});
document.addEventListener('webkitfullscreenchange', function() {{
  var wrap = document.getElementById('viewer-wrap');
  if (!document.webkitFullscreenElement) wrap.classList.remove('is-fullscreen');
  setTimeout(function() {{
    if (_PLOT_GD) Plotly.Plots.resize(_PLOT_GD);
  }}, 120);
}});

// Responsive resize
window.addEventListener('resize', function() {{
  if (_PLOT_GD) Plotly.Plots.resize(_PLOT_GD);
}});
"""


def _animation_js(frame_names: List[str], base_ms: int,
                  phase_config: Dict, total_steps: int) -> str:
    frames_j   = json.dumps([str(n) for n in frame_names])
    phases_j   = json.dumps(phase_config)
    total_j    = int(total_steps)
    s1e = phase_config.get("stage1_end", 20_000)
    s2e = phase_config.get("stage2_end", 40_000)
    s3e = phase_config.get("stage3_end", 60_000)
    ms  = phase_config.get("moisture_start", 60_000)

    return f"""
var _FRAMES   = {frames_j};
var _BASE_MS  = {base_ms};
var _curMS    = {base_ms};
var _PHASES   = {phases_j};
var _TOTAL    = {total_j};
var _playing  = false;

function _getPhase(step) {{
  var s = parseInt(step);
  if (s < {s1e}) return 'Stage 1 \u2014 Hydrostatic spin-up';
  if (s < {s2e}) return 'Stage 2 \u2014 Thermal forcing';
  if (s < {s3e}) return 'Stage 3 \u2014 Rotation & circulation';
  return 'Stage 4 \u2014 Moisture physics';
}}

function _updateDisplay(frameName) {{
  var n = parseInt(frameName) || 0;
  var sEl = document.getElementById('cur-step');
  var pEl = document.getElementById('cur-phase');
  var bEl = document.getElementById('cur-bar');
  if (sEl) sEl.textContent = n.toLocaleString();
  if (pEl) pEl.textContent = _getPhase(n);
  if (bEl && _TOTAL > 0) {{
    bEl.style.width = Math.min(100, Math.round(n / _TOTAL * 100)) + '%';
  }}
}}

function playAnim() {{
  _playing = true;
  document.getElementById('btn-play').classList.add('active');
  document.getElementById('btn-pause').classList.remove('active');
  Plotly.animate(_PLOT_GD, null, {{
    frame: {{duration: _curMS, redraw: true}},
    fromcurrent: true,
    transition: {{duration: Math.round(_curMS * 0.35)}}
  }});
}}

function pauseAnim() {{
  _playing = false;
  document.getElementById('btn-play').classList.remove('active');
  document.getElementById('btn-pause').classList.add('active');
  Plotly.animate(_PLOT_GD, [null], {{
    frame: {{duration: 0, redraw: false}},
    mode: 'immediate', transition: {{duration: 0}}
  }});
}}

function restartAnim() {{
  pauseAnim();
  setTimeout(function() {{
    if (!_FRAMES.length) return;
    Plotly.animate(_PLOT_GD, [_FRAMES[0]], {{
      frame: {{duration: 0, redraw: true}},
      mode: 'immediate', transition: {{duration: 0}}
    }});
    _updateDisplay(_FRAMES[0]);
    document.getElementById('btn-pause').classList.remove('active');
  }}, 60);
}}

function setSpeed(mult, btnId) {{
  _curMS = Math.max(60, Math.round(_BASE_MS / mult));
  document.querySelectorAll('.spd-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  var b = document.getElementById(btnId);
  if (b) b.classList.add('active');
  if (_playing) {{
    Plotly.animate(_PLOT_GD, null, {{
      frame: {{duration: _curMS, redraw: true}},
      fromcurrent: true,
      transition: {{duration: Math.round(_curMS * 0.35)}}
    }});
  }}
}}

// Hook into Plotly's animation events to update the step display.
// _PLOT_GD was set by the viewer base JS; poll briefly if not yet available.
function _attachAnimEvents() {{
  if (!_PLOT_GD) {{
    _PLOT_GD = window._VIEWER_GD
               || document.querySelector('.js-plotly-plot')
               || document.querySelector('.plotly-graph-div');
  }}
  if (_PLOT_GD) {{
    _PLOT_GD.on('plotly_animatingframe', function(d) {{
      if (d && d.name) _updateDisplay(d.name);
    }});
    _PLOT_GD.on('plotly_animated', function() {{
      _playing = false;
      var b = document.getElementById('btn-play');
      if (b) b.classList.remove('active');
    }});
  }}
  if (_FRAMES.length) _updateDisplay(_FRAMES[0]);
  var s = document.getElementById('spd-1x');
  if (s) s.classList.add('active');
}}
document.addEventListener('DOMContentLoaded', _attachAnimEvents);
"""


# ──────────────────────────────────────────────────────────────────────────
# Mode navigation HTML
# ──────────────────────────────────────────────────────────────────────────

def _mode_nav_html(modes: List[Tuple[str, str]], active_stem: str,
                   nav_label: str = "View mode") -> str:
    items = []
    for label, fname in modes:
        active = "active" if (active_stem in fname) else ""
        items.append(
            f'<a class="mnav-btn {active}" href="{fname}">{label}</a>'
        )
    sep = '<div class="mnav-sep"></div>'
    return (
        f'<div class="mode-nav">'
        f'<span class="mode-nav-label">{nav_label}</span>'
        + sep.join(items)
        + f'</div>'
    )


# ──────────────────────────────────────────────────────────────────────────
# Phase timeline HTML
# ──────────────────────────────────────────────────────────────────────────

def _phase_timeline_html(frame_names: List[str],
                         cfg: Optional[Dict] = None) -> str:
    c = cfg or PHASE_CONFIG
    s1e = c.get("stage1_end",     20_000)
    s2e = c.get("stage2_end",     40_000)
    s3e = c.get("stage3_end",     60_000)
    ms  = c.get("moisture_start", 60_000)

    steps = sorted(int(n) for n in frame_names if str(n).isdigit())
    if not steps:
        return ""
    mn, mx = steps[0], steps[-1]
    span   = mx - mn if mx != mn else 1

    def pct(v: int) -> str:
        return f"{max(0, min(100, round((v - mn) / span * 100)))}%"

    markers = [
        (mn,  "s1", f"Stage&nbsp;1<br>{mn//1000}k" if mn > 0 else "Stage&nbsp;1<br>0"),
        (s1e, "s2", f"Stage&nbsp;2<br>{s1e//1000}k"),
        (s2e, "s3", f"Stage&nbsp;3<br>{s2e//1000}k"),
        (ms,  "s4", f"Moisture<br>{ms//1000}k"),
        (mx,  "s4", f"End<br>{mx//1000}k"),
    ]
    marks_html = ""
    seen = set()
    for v, cls, lbl in markers:
        if v < mn or v > mx or v in seen:
            continue
        seen.add(v)
        marks_html += (
            f'<div class="pt-marker" style="left:{pct(v)}">'
            f'<div class="pt-tick {cls}"></div>'
            f'<div class="pt-mlabel">{lbl}</div>'
            f'</div>'
        )

    return f"""
<div class="phase-timeline">
  <div class="pt-header">Simulation timeline</div>
  <div class="pt-track">
    <div class="pt-progress" id="cur-bar"></div>
    {marks_html}
  </div>
</div>"""


# ──────────────────────────────────────────────────────────────────────────
# Animation controls bar HTML
# ──────────────────────────────────────────────────────────────────────────

def _anim_controls_html() -> str:
    return """
<div class="anim-bar">
  <div class="anim-group">
    <span class="anim-label">Playback</span>
    <button class="abtn active" id="btn-play"  onclick="playAnim()">&#9654; Play</button>
    <button class="abtn"        id="btn-pause" onclick="pauseAnim()">&#9646;&#9646; Pause</button>
    <button class="abtn"        onclick="restartAnim()">&#8635; Restart</button>
  </div>
  <div class="anim-group">
    <span class="anim-label">Speed</span>
    <button class="abtn spd-btn" id="spd-0p5x"
            onclick="setSpeed(0.5,'spd-0p5x')">0.5&times;</button>
    <button class="abtn spd-btn" id="spd-1x"
            onclick="setSpeed(1,'spd-1x')">1&times;</button>
    <button class="abtn spd-btn" id="spd-2x"
            onclick="setSpeed(2,'spd-2x')">2&times;</button>
  </div>
</div>
<div class="step-display">
  <div class="sditem"><b>Step:</b>&nbsp;<span id="cur-step">&#8212;</span></div>
  <div class="sditem"><b>Phase:</b>&nbsp;<span id="cur-phase">&#8212;</span></div>
</div>"""


# ──────────────────────────────────────────────────────────────────────────
# Core page builder
# ──────────────────────────────────────────────────────────────────────────

def _render_page(
    plot_html: str,
    page_title: str,
    subtitle: str,
    step_str: str,
    phase_str: str,
    n_particles: int,
    mode_nav_html: str,
    is_animation: bool,
    frame_names: Optional[List[str]],
    base_ms: int,
    phase_config: Dict,
    total_steps: int,
    camera: Dict,
    extra_tool_html: str = "",
) -> str:
    """Assemble a complete professional HTML page."""
    css = _page_css()

    header_html = f"""
<header class="vhdr">
  <a class="vhdr-brand" href="../index.html">&#x2B21; AtmosphericSim</a>
  <div class="vhdr-titles">
    <div class="vhdr-title">{page_title}</div>
    <div class="vhdr-sub">{subtitle}</div>
  </div>
  <div class="vhdr-meta">
    <span class="vmeta-item"><b>Step:</b> {step_str}</span>
    <span class="vmeta-item"><b>Phase:</b> {phase_str}</span>
    <span class="vmeta-item"><b>Displayed:</b> {n_particles:,} particles</span>
    <span class="vmeta-item"><b>Geometry:</b> Spherical shell</span>
  </div>
</header>"""

    anim_bar   = _anim_controls_html() if is_animation else ""
    phase_tl   = (_phase_timeline_html(frame_names or [], phase_config)
                  if is_animation else "")

    toolbar_html = f"""
<div class="toolbar">
  <button class="tbtn" onclick="resetCamera()">&#8635; Reset Camera</button>
  <button class="tbtn" onclick="toggleFullscreen()">&#x26F6; Fullscreen</button>
  {extra_tool_html}
</div>"""

    base_js  = _base_viewer_js(camera, page_title)
    extra_js = (_animation_js(frame_names or [], base_ms, phase_config, total_steps)
                if is_animation else "")

    footer_html = """
<footer class="vfooter">
  <span>AtmosphericSimulation &mdash; Stage UI-4 Visualization</span>
  <span>Generated by build_dashboard.py</span>
  <a href="../index.html">&larr; Back to dashboard</a>
</footer>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{page_title} &mdash; AtmosphericSimulation</title>
  <style>{css}</style>
</head>
<body>
{header_html}
{mode_nav_html}
{anim_bar}
<div class="plot-outer" id="viewer-wrap">
{toolbar_html}
{plot_html}
</div>
{phase_tl}
{footer_html}
<script>
{base_js}
{extra_js}
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────
# Public API: write_viewer_page / write_animation_page
# ──────────────────────────────────────────────────────────────────────────

def write_viewer_page(
    fig: Any,
    out_path: str,
    var_name: str,
    step: int,
    n_particles: int,
    inner_r: float = DEFAULT_INNER_RADIUS,
    outer_r: float = DEFAULT_OUTER_RADIUS,
) -> None:
    """Write a professional static 3D viewer HTML page."""
    cfg  = VARIABLE_CONFIG.get(var_name, {})
    cam  = get_camera()
    phase = get_phase_name(step)
    step_str = f"{step:,}"

    # post_script runs after Plotly.newPlot — 'gd' is the graph div.
    # Works in Plotly 4.x and 5.x (div_id param only available in 5.x).
    post_script = "window._VIEWER_GD = gd;"
    plot_html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=True,
        post_script=post_script,
        config={
            "responsive": True,
            "displaylogo": False,
            "scrollZoom": True,
            "modeBarButtonsToRemove": ["toImage"],
        },
    )

    mode_nav = _mode_nav_html(
        VIEWER_MODES,
        active_stem=cfg.get("col_key", ""),
        nav_label="View mode",
    )

    page = _render_page(
        plot_html=plot_html,
        page_title=cfg.get("page_title", "3D Particle Viewer"),
        subtitle=cfg.get("subtitle", ""),
        step_str=step_str,
        phase_str=phase,
        n_particles=n_particles,
        mode_nav_html=mode_nav,
        is_animation=False,
        frame_names=None,
        base_ms=BASE_FRAME_MS,
        phase_config=PHASE_CONFIG,
        total_steps=100_000,
        camera=cam,
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)


def write_animation_page(
    fig: Any,
    out_path: str,
    var_name: str,
    frame_names: List[str],
    first_step: int,
    last_step: int,
    n_particles: int,
    inner_r: float = DEFAULT_INNER_RADIUS,
    outer_r: float = DEFAULT_OUTER_RADIUS,
    base_ms: int = BASE_FRAME_MS,
) -> None:
    """Write a professional animated 3D particle viewer HTML page."""
    cfg   = VARIABLE_CONFIG.get(var_name, {})
    cam   = get_camera()
    phase = get_phase_name(first_step)

    var_labels = {
        "T_p":     "3D Atmospheric Particle Animation",
        "v_r":     "3D Atmospheric Particle Animation",
        "v_theta": "3D Atmospheric Particle Animation",
        "q_p":     "3D Atmospheric Particle Animation",
    }
    page_title = var_labels.get(var_name, "3D Atmospheric Particle Animation")
    subtitle   = cfg.get("subtitle", "").replace("Viewer", "Animation")

    post_script_anim = "window._VIEWER_GD = gd;"
    plot_html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=True,
        post_script=post_script_anim,
        config={
            "responsive": True,
            "displaylogo": False,
            "scrollZoom": True,
        },
        auto_play=False,
    )

    mode_nav = _mode_nav_html(
        ANIMATION_MODES,
        active_stem=cfg.get("col_key", ""),
        nav_label="Animation mode",
    )

    page = _render_page(
        plot_html=plot_html,
        page_title=page_title,
        subtitle=subtitle,
        step_str=f"{first_step:,} \u2013 {last_step:,}",
        phase_str=phase,
        n_particles=n_particles,
        mode_nav_html=mode_nav,
        is_animation=True,
        frame_names=frame_names,
        base_ms=base_ms,
        phase_config=PHASE_CONFIG,
        total_steps=last_step,
        camera=cam,
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
