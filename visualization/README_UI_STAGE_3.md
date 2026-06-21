# Stage UI-3 — Visualization Builder

## What Stage UI-3 Does

Stage UI-3 reads the CSV files produced by the C++ AtmosphericSimulation engine
and generates a complete visualization package under `visualization_output/`:

| Output type | Directory | Description |
|---|---|---|
| Interactive HTML figures | `visualization_output/html/` | Plotly charts, fully offline |
| Dashboard preview PNGs | `visualization_output/png/` | 120 DPI matplotlib figures |
| Report-ready PNGs | `visualization_output/report_figures/` | 300 DPI for publication |
| Animations | `visualization_output/animations/` | GIF + Plotly slider animations |
| Summary JSONs | `visualization_output/summary/` | Diagnostic status data |
| Updated manifest | `visualization_output/assets/generated_manifest.js` | Dashboard data layer |

The dashboard (`visualization_output/index.html`) works completely **offline**
from `file://` — no server, no fetch(), no internet required.

**Stage UI-3 does NOT modify any C++ source files, `src/`, `CMakeLists.txt`,
or any simulation/physics logic.  It only reads existing CSV files.**

---

## Installation

### Option A — Virtual environment (recommended)

```bash
python3 -m venv viz_env
source viz_env/bin/activate
pip install -r visualization/requirements.txt
```

### Option B — System-wide (may need sudo)

```bash
pip install -r visualization/requirements.txt --break-system-packages
```

### Dependencies

```
pandas     — CSV reading and data manipulation
numpy      — Numerical operations and binning
matplotlib — PNG / 300-DPI static figures
plotly     — Interactive HTML figures
imageio    — GIF animation generation (optional; skipped gracefully if unavailable)
kaleido    — Plotly static PNG export (optional; matplotlib fallback used if absent)
```

---

## Running the Visualization Builder

### Basic run (reads `output/`, writes to `visualization_output/`)

```bash
python3 visualization/build_dashboard.py
```

### With all options

```bash
python3 visualization/build_dashboard.py \
  --input output \
  --out visualization_output \
  --max-particles 5000 \
  --verbose
```

### Skip animations (faster for quick iteration)

```bash
python3 visualization/build_dashboard.py --skip-animation
```

### Open dashboard when done

```bash
python3 visualization/build_dashboard.py --open-dashboard
```

---

## Command-Line Options

| Flag | Default | Description |
|---|---|---|
| `--input DIR` | `output` | Input CSV directory |
| `--out DIR` | `visualization_output` | Output root directory |
| `--max-particles N` | `5000` | Max particles for 3D/animation (downsampled deterministically) |
| `--skip-animation` | off | Skip animation generation |
| `--open-dashboard` | off | Open `index.html` in browser when done |
| `--verbose` | off | Print per-file progress |

---

## Opening the Dashboard

**Windows / WSL:**
```
explorer.exe visualization_output/index.html
```

**macOS:**
```
open visualization_output/index.html
```

**Linux:**
```
xdg-open visualization_output/index.html
```

Or simply double-click `visualization_output/index.html` in your file manager.

---

## Expected Input Files

The script auto-detects which CSV files are available.  It skips any missing
file with a warning rather than crashing.

| File | Used for |
|---|---|
| `output/temperature_zones.csv` | Temperature zones time-series |
| `output/moisture_balance.csv` | Water-balance panels + status |
| `output/evaporation_log.csv` | Evaporation time-series |
| `output/condensation_log.csv` | Condensation time-series |
| `output/simulation_log.csv` | Simulation energy diagnostic |
| `output/altitude_temperature_profile.csv` | Altitude–temperature profile |
| `output/streamfunction_summary.csv` | max\|Ψ\| vs time chart |
| `output/streamfunction_step_*.csv` | Streamfunction Ψ heatmap |
| `output/particles_step_*.csv` | 3D viewers, animations |
| `output/particle_spherical_step_*.csv` | 3D viewers, moisture heatmaps |
| `output/circulation_accum_step_*.csv` | v_theta heatmap |

---

## Generated Output Files

### Always generated (when source CSV exists)

```
visualization_output/
├── html/
│   ├── temperature_zones_timeseries.html
│   ├── water_balance_panels.html
│   └── evap_cond_timeseries.html
├── png/
│   ├── temperature_zones_timeseries.png
│   ├── water_balance_panels.png
│   ├── evap_cond_timeseries.png
│   ├── evap_cond_rates_only.png
│   ├── evap_cond_cumulative_only.png
│   └── simulation_energy.png
├── report_figures/
│   ├── temperature_zones_timeseries_300dpi.png
│   ├── water_balance_panels_300dpi.png
│   ├── evap_cond_timeseries_300dpi.png
│   ├── evap_cond_rates_only_300dpi.png
│   └── evap_cond_cumulative_only_300dpi.png
└── summary/
    ├── dashboard_summary.json
    ├── water_balance_summary.json
    └── evap_cond_summary.json
```

### Generated when particle snapshot CSVs exist

```
visualization_output/
├── html/
│   ├── particle_3d_temperature.html
│   ├── particle_3d_vr.html
│   ├── particle_3d_vtheta.html
│   ├── particle_3d_qp.html
│   ├── particle_animation_temperature.html
│   ├── particle_animation_qp.html
│   ├── humidity_lat_alt_heatmap.html
│   ├── vtheta_heatmap.html
│   └── streamfunction_heatmap_contours.html
├── png/
│   ├── humidity_lat_alt_heatmap.png
│   ├── vtheta_heatmap.png
│   └── streamfunction_heatmap_contours.png
├── report_figures/
│   ├── humidity_lat_alt_heatmap_300dpi.png
│   ├── vtheta_heatmap_300dpi.png
│   └── streamfunction_heatmap_contours_300dpi.png
└── animations/
    └── particle_animation_preview.gif
```

---

## Water Balance Status

The script computes a recommended diagnostic status from `moisture_balance.csv`:

| Status | Condition |
|---|---|
| `PASS` | max relative error ≤ 1×10⁻⁴ |
| `WARNING` | max relative error ≤ 1×10⁻² |
| `FAIL` | max relative error > 1×10⁻² |
| `NOT_AVAILABLE` | `moisture_balance.csv` missing |

This status is embedded in `generated_manifest.js` and displayed in the
validation section of the dashboard — **without any fetch() call**.

---

## Module Structure

```
visualization/
├── build_dashboard.py     — Main entry point, argparse, orchestration
├── data_loader.py         — CSV I/O, column aliases, downsampling
├── plot_timeseries.py     — Temperature zones, max|Ψ|, altitude profile
├── plot_moisture.py       — Water balance, evap/cond, moisture heatmaps
├── plot_heatmaps.py       — Streamfunction, v_theta, temp lat–alt
├── plot_particles_3d.py   — Interactive 3D scatter viewers
├── animation_builder.py   — Plotly animation + GIF builder
├── manifest_builder.py    — Generates generated_manifest.js
├── requirements.txt       — Python dependencies
└── README_UI_STAGE_3.md   — This file
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'pandas'`
Install dependencies first:
```bash
pip install -r visualization/requirements.txt
```
Or use a virtual environment (see Installation above).

### `[WARN] moisture_balance.csv not found`
The C++ simulation has not been run yet, or the output directory is wrong.
Run the simulation first, then pass the correct `--input` path.

### `[WARN] No particle snapshot file found — skipping 3D viewers`
The simulation did not produce `particles_step_*.csv` output files.
This is expected if the simulation was configured without per-step snapshots.
Only the scalar CSV diagnostics (temperature zones, moisture balance, etc.)
will be plotted.

### Plotly HTML files are very large
Each file embeds the Plotly.js library (~3 MB) for offline compatibility.
Use `--max-particles` to reduce the particle count in 3D viewers and animations.

### GIF generation fails
Install `imageio`:
```bash
pip install imageio
```
If it still fails, the script falls back to Plotly HTML-only animation and
a matplotlib PNG preview.

### The dashboard shows all "N/A" badges
Run `python3 visualization/build_dashboard.py` at least once to generate the
manifest.  The stub manifest shipped with Stage UI-2 will be replaced.

---

## Full Pipeline

To build the C++ project, run the simulation, and generate visualizations
in one step:

```bash
bash run_full_pipeline.sh
bash run_full_pipeline.sh --skip-animation   # faster
bash run_full_pipeline.sh --open-dashboard   # open browser when done
```

---

## Scientific Wording Note

All plot titles and dashboard text use cautious, diagnostic language:
- "simulation diagnostic" — not "proven result"
- "candidate meridional circulation" — not "Hadley cell confirmed"
- "moisture diagnostic" — not "real water cycle reproduced"

This reflects the fact that a toy particle-based model produces
*qualitative illustrations* of atmospheric dynamics, not calibrated
physical predictions.

---

## Next Step — Stage UI-4

Stage UI-4 (optional) could include:
- VTK/ParaView export for volumetric rendering
- PDF report generation from the 300-DPI PNGs
- Streamlit or Dash interactive app (server-based)
- Automated regression testing of diagnostic thresholds
