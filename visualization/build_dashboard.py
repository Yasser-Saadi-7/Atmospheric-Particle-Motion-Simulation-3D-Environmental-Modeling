#!/usr/bin/env python3
"""
build_dashboard.py — Stage UI-3
==========================================================
Main entry point for the AtmosphericSimulation visualization
pipeline.  Reads CSV files from output/ and generates a complete
visualization package under visualization_output/.

Usage:
    python3 visualization/build_dashboard.py
    python3 visualization/build_dashboard.py \\
        --input output --out visualization_output \\
        --max-particles 5000 --verbose

This script NEVER modifies C++ source files, src/, CMakeLists.txt,
or any simulation/physics logic.  It only reads CSVs from output/.
==========================================================
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---- Make sibling modules importable ----------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    from data_loader import ensure_output_dirs, find_step_files, find_latest_file
    from manifest_builder import build_manifest, load_json_summary
except ImportError as _err:
    print(f"\n  [ERROR] Missing Python dependency: {_err}")
    print("\n  Install requirements:")
    print("    python3 -m venv viz_env")
    print("    source viz_env/bin/activate")
    print("    pip install -r visualization/requirements.txt")
    print("\n  Or (system-wide):")
    print("    pip install -r visualization/requirements.txt --break-system-packages")
    sys.exit(1)


# ------------------------------------------------------------------
# Argument parsing
# ------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AtmosphericSimulation — Stage UI-3 visualization builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 visualization/build_dashboard.py\n"
            "  python3 visualization/build_dashboard.py --input output "
            "--out visualization_output --max-particles 3000 --verbose\n"
            "  python3 visualization/build_dashboard.py --skip-animation "
            "--open-dashboard\n"
        ),
    )
    parser.add_argument("--input",          default="output",
                        metavar="DIR",      help="Input CSV directory  (default: output)")
    parser.add_argument("--out",            default="visualization_output",
                        metavar="DIR",      help="Output directory      (default: visualization_output)")
    parser.add_argument("--max-particles",  type=int, default=5000,
                        metavar="N",        help="Max particles for 3D/animation (default: 5000)")
    parser.add_argument("--skip-animation", action="store_true",
                        help="Skip animation generation (saves time)")
    parser.add_argument("--open-dashboard", action="store_true",
                        help="Open index.html in browser when done")
    parser.add_argument("--verbose",        action="store_true",
                        help="Print per-file progress")
    return parser.parse_args()


# ------------------------------------------------------------------
# Section banner helpers
# ------------------------------------------------------------------

_W = 64

def banner(msg: str, idx: int = 0, total: int = 0) -> None:
    step_str = f"[{idx}/{total}] " if idx else ""
    print(f"\n  {step_str}{msg}")
    print("  " + "─" * (_W - 2))


def header() -> None:
    print("=" * _W)
    print("  AtmosphericSimulation — Stage UI-3 Visualization Builder")
    print("=" * _W)


def footer(generated: List[str], warnings: List[str], t0: float, out_dir: str) -> None:
    elapsed = time.time() - t0
    print("\n" + "=" * _W)
    print("  SUMMARY")
    print("=" * _W)
    print(f"  Generated : {len(generated)} file(s)")
    print(f"  Warnings  : {len(warnings)}")
    print(f"  Elapsed   : {elapsed:.1f} s")
    if warnings:
        print("\n  Warnings:")
        for w in warnings:
            print(f"    • {w}")
    print(f"\n  Open dashboard:")
    idx_path = os.path.join(out_dir, "index.html")
    if platform.system() == "Windows":
        print(f"    start {idx_path}")
    elif sys.platform.startswith("linux"):
        print(f"    explorer.exe {idx_path}   (WSL)")
        print(f"    — or open directly in Windows File Explorer")
    else:
        print(f"    open {idx_path}")
    print("=" * _W + "\n")


# ------------------------------------------------------------------
# CSV inventory
# ------------------------------------------------------------------

def inventory_csvs(input_dir: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Detect which CSV files are available in input_dir.
    In verbose mode, also prints the latest filename selected for each
    multi-step pattern so the user can confirm numeric-step ordering.
    """
    from data_loader import find_latest_file as _latest

    checks = [
        ("particles_step_*.csv",             "particle_snapshots"),
        ("particle_spherical_step_*.csv",    "particle_spherical"),
        ("coarse_grid_step_*.csv",           "coarse_grid"),
        ("streamfunction_step_*.csv",        "streamfunction_steps"),
        ("streamfunction_summary.csv",       "streamfunction_summary"),
        ("temperature_zones.csv",            "temperature_zones"),
        ("altitude_temperature_profile.csv", "altitude_temp_profile"),
        ("simulation_log.csv",               "simulation_log"),
        ("evaporation_log.csv",              "evaporation_log"),
        ("condensation_log.csv",             "condensation_log"),
        ("moisture_balance.csv",             "moisture_balance"),
        ("circulation_accum_step_*.csv",     "circulation_accum"),
    ]
    found: Dict[str, Any] = {}
    for pattern, key in checks:
        if "*" in pattern:
            files = find_step_files(input_dir, pattern)
            found[key] = files
        else:
            fpath = os.path.join(input_dir, pattern)
            found[key] = fpath if os.path.isfile(fpath) else None

    if verbose:
        print(f"  Input folder : {os.path.abspath(input_dir)}")
        print("  Detected CSV files:")
        for pattern, key in checks:
            val = found[key]
            if isinstance(val, list):
                n = len(val)
                suffix = ""
                if n > 0:
                    latest = _latest(input_dir, pattern)
                    suffix = f" — latest: {os.path.basename(latest)}" if latest else ""
                status = f"{n} file(s){suffix}"
            else:
                status = "✓" if val else "— missing"
            print(f"    {key:35s}: {status}")
    return found


# ------------------------------------------------------------------
# Validation CSV copy + markdown summary
# ------------------------------------------------------------------

# CSVs to copy from input → validation/
_VALIDATION_CSV_NAMES = [
    "moisture_balance.csv",
    "temperature_zones.csv",
    "evaporation_log.csv",
    "condensation_log.csv",
    "simulation_log.csv",
    "streamfunction_summary.csv",
]


def _copy_validation_files(
    input_dir: str,
    out_dir: str,
    wb_summary: Optional[Dict[str, Any]],
    verbose: bool = False,
) -> List[str]:
    """
    Copy validation CSV files from `input_dir` to
    `out_dir/validation/` and write two markdown summaries.
    Returns a list of copied/created file paths.
    """
    import shutil

    val_dir = os.path.join(out_dir, "validation")
    Path(val_dir).mkdir(parents=True, exist_ok=True)
    created: List[str] = []
    copied_names: List[str] = []

    for fname in _VALIDATION_CSV_NAMES:
        src = os.path.join(input_dir, fname)
        if os.path.isfile(src):
            dst = os.path.join(val_dir, fname)
            shutil.copy2(src, dst)
            created.append(dst)
            copied_names.append(fname)
            if verbose:
                print(f"  [OK] validation/{fname}")
        else:
            if verbose:
                print(f"  [--] validation/{fname}  (not found in input)")

    # ---- visualization_validation_summary.md -------------------------
    vis_md = os.path.join(val_dir, "visualization_validation_summary.md")
    with open(vis_md, "w", encoding="utf-8") as fh:
        fh.write("# Visualization Validation Summary\n\n")
        fh.write(
            "*Auto-generated by build_dashboard.py — "
            f"updated {datetime.now().strftime('%Y-%m-%d %H:%M')}.*\n\n"
        )
        fh.write("## Copied validation data files\n\n")
        if copied_names:
            for n in copied_names:
                fh.write(f"- `{n}`\n")
        else:
            fh.write("*No validation CSVs found in input folder.*\n")
        fh.write(
            "\n## Notes\n\n"
            "- These files are copied directly from the simulation output folder.\n"
            "- They are provided for reference only; no physical validation is performed "
            "by this script.\n"
            "- PASS/WARNING/FAIL status is derived solely from water-balance diagnostics "
            "and does not constitute a scientific validation.\n"
        )
    created.append(vis_md)
    if verbose:
        print(f"  [OK] validation/visualization_validation_summary.md")

    # ---- water_balance_summary.md ------------------------------------
    wb_md = os.path.join(val_dir, "water_balance_summary.md")
    wb_status = (wb_summary or {}).get("recommended_status", "NOT_AVAILABLE")
    wb_rel_err = (wb_summary or {}).get("max_relative_error_pct", "N/A")
    with open(wb_md, "w", encoding="utf-8") as fh:
        fh.write("# Water Balance Summary\n\n")
        fh.write(
            "*Auto-generated by build_dashboard.py — "
            f"updated {datetime.now().strftime('%Y-%m-%d %H:%M')}.*\n\n"
        )
        fh.write(f"**Recommended status:** `{wb_status}`\n\n")
        if wb_status == "NOT_AVAILABLE":
            fh.write(
                "Water balance diagnostics could not be computed "
                "(moisture_balance.csv not found or empty).\n"
            )
        else:
            fh.write(
                f"Max relative error: `{wb_rel_err}%`\n\n"
                "Status key:\n"
                "- `PASS`    — relative error < 1%\n"
                "- `WARNING` — relative error 1–5%\n"
                "- `FAIL`    — relative error > 5%\n"
                "- `NOT_AVAILABLE` — no moisture balance data\n\n"
                "> This status is a heuristic diagnostic, not a scientific validation.\n"
            )
    created.append(wb_md)
    if verbose:
        print(f"  [OK] validation/water_balance_summary.md")

    return created


# ------------------------------------------------------------------
# ASCII VTK particle writer (stdlib only, no heavy dependencies)
# ------------------------------------------------------------------

def _write_vtk_particles(
    input_dir: str,
    out_dir: str,
    max_pts: int = 50000,
    verbose: bool = False,
) -> List[str]:
    """Write an ASCII VTK Legacy PolyData file from the latest particle CSV.

    Uses only Python standard library (csv module).  No non-ASCII characters
    are written — VTK Legacy format is strict 7-bit ASCII.
    """
    import csv as _csv

    vtk_dir = os.path.join(out_dir, "vtk")
    os.makedirs(vtk_dir, exist_ok=True)

    # Find source file
    from data_loader import find_latest_file
    src = find_latest_file(input_dir, "particle_spherical_step_*.csv")
    if src is None:
        src = find_latest_file(input_dir, "particles_step_*.csv")
    if src is None:
        print("  [WARN] VTK: no particle snapshot found - skipping.")
        return []

    stem = os.path.splitext(os.path.basename(src))[0].replace("particle_spherical_", "particles_")
    vtk_path = os.path.join(vtk_dir, stem + ".vtk")

    if verbose:
        print(f"  [VTK] Source : {os.path.relpath(src)}")
        print(f"  [VTK] Output : {os.path.relpath(vtk_path)}")

    try:
        with open(src, newline="", encoding="utf-8") as fh:
            reader = _csv.DictReader(fh)
            rows = list(reader)
    except Exception as exc:
        print(f"  [WARN] VTK: could not read CSV: {exc}")
        return []

    if not rows:
        print("  [WARN] VTK: empty particle CSV.")
        return []

    # Column detection (direct match, no aliases needed here)
    header = list(rows[0].keys())
    def _col(*names):
        for n in names:
            if n in header:
                return n
        return None

    cx  = _col("x")
    cy  = _col("y")
    cz  = _col("z")
    ct  = _col("temperature", "T_p", "temp", "T")
    cr  = _col("v_r", "vr", "radial_velocity")
    cvt = _col("v_theta", "vtheta", "meridional_velocity")
    cvp = _col("v_phi_relative", "v_phi_inertial", "v_phi")
    cq  = _col("q_p", "specificHumidity", "q")
    ca  = _col("altitude", "alt", "height")
    cra = _col("radius", "r")

    if not cx or not cy or not cz:
        print(f"  [WARN] VTK: x/y/z columns not found in CSV (found: {header[:8]}) - skipping.")
        # Remove any partial file from a prior failed run
        if os.path.exists(vtk_path):
            os.remove(vtk_path)
        return []

    if verbose:
        scalar_cols = [c for c in [ct, cr, cvt, cvp, cq, ca, cra] if c]
        print(f"  [VTK] Position columns : x={cx}, y={cy}, z={cz}")
        print(f"  [VTK] Scalar columns   : {scalar_cols}")
        print(f"  [VTK] Total rows       : {len(rows):,}")

    # Subsample if needed
    if len(rows) > max_pts:
        step2 = max(1, len(rows) // max_pts)
        rows = rows[::step2]
    n_pts = len(rows)

    # Parse floats
    def _flt(row, col, default=0.0):
        try:
            return float(row[col]) if col else default
        except (ValueError, KeyError, TypeError):
            return default

    points  = [[_flt(r, cx), _flt(r, cy), _flt(r, cz)] for r in rows]
    scalars = {}
    for name, col in [("temperature", ct), ("v_r", cr), ("v_theta", cvt),
                       ("v_phi_relative", cvp), ("q_p", cq),
                       ("altitude", ca), ("radius", cra)]:
        if col:
            scalars[name] = [_flt(r, col) for r in rows]

    # Write VTK Legacy ASCII PolyData — strict 7-bit ASCII, no Unicode
    tmp_path = vtk_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="ascii") as out:
            out.write("# vtk DataFile Version 3.0\n")
            # Title line must be < 256 chars, ASCII only
            out.write(f"AtmosphericSimulation particle export - {stem}\n")
            out.write("ASCII\n")
            out.write("DATASET POLYDATA\n")
            out.write(f"POINTS {n_pts} float\n")
            for p in points:
                out.write(f"{p[0]:.6g} {p[1]:.6g} {p[2]:.6g}\n")

            # Each particle is a VTK vertex cell (1 point per cell)
            out.write(f"\nVERTICES {n_pts} {n_pts * 2}\n")
            for i in range(n_pts):
                out.write(f"1 {i}\n")

            # Scalar point data
            out.write(f"\nPOINT_DATA {n_pts}\n")
            first = True
            for name, vals in scalars.items():
                out.write(f"SCALARS {name} float 1\n")
                out.write("LOOKUP_TABLE default\n")
                for v in vals:
                    out.write(f"{v:.6g}\n")
                first = False

        # Atomically replace (avoids a half-written file being seen)
        if os.path.exists(vtk_path):
            os.remove(vtk_path)
        os.rename(tmp_path, vtk_path)

    except Exception as exc:
        print(f"  [ERROR] VTK write failed: {exc}")
        for p in [tmp_path, vtk_path]:
            try:
                os.remove(p)
            except OSError:
                pass
        return []

    size_kb = os.path.getsize(vtk_path) // 1024
    print(f"  [OK]  VTK export: {os.path.relpath(vtk_path)} "
          f"({n_pts:,} particles, {len(scalars)} scalars, {size_kb} kB)")
    return [vtk_path]


def _is_valid_vtk(path: str) -> bool:
    """Return True if the VTK file looks complete (has POINTS and POINT_DATA)."""
    try:
        with open(path, encoding="ascii", errors="ignore") as fh:
            content = fh.read(8192)  # First 8 kB is enough for section headers
        return "DATASET" in content and "POINTS" in content and "POINT_DATA" in content
    except Exception:
        return False


def _vtk_is_available(out_dir: str) -> bool:
    """Return True if a valid VTK file exists under visualization_output/vtk/."""
    vtk_dir = os.path.join(out_dir, "vtk")
    if not os.path.isdir(vtk_dir):
        return False
    for fname in os.listdir(vtk_dir):
        if fname.endswith(".vtk") and _is_valid_vtk(os.path.join(vtk_dir, fname)):
            return True
    return False


# ------------------------------------------------------------------
# Main orchestration
# ------------------------------------------------------------------

def main() -> None:
    args    = parse_args()
    t0      = time.time()
    generated: List[str] = []
    warnings: List[str]  = []

    header()
    print(f"  Input  : {os.path.abspath(args.input)}")
    print(f"  Output : {os.path.abspath(args.out)}")
    print(f"  Particles limit : {args.max_particles:,}")

    # Validate input directory
    if not os.path.isdir(args.input):
        print(f"\n  [ERROR] Input directory '{args.input}' does not exist.")
        print("          Run the C++ simulation first to produce CSV files.")
        sys.exit(1)

    # Ensure all output subdirectories exist
    ensure_output_dirs(args.out)

    # Reset missing-outputs report so each run is fresh
    _missing_md = os.path.join(args.out, "summary", "missing_required_outputs.md")
    with open(_missing_md, "w", encoding="utf-8") as _fh:
        _fh.write("# Missing Required Outputs\n\n"
                  "*Auto-generated by build_dashboard.py — regenerated on each run.*\n")

    # Detect available data
    banner("Scanning input CSV files", 1, 10)
    inv = inventory_csvs(args.input, verbose=args.verbose)

    # ------------------------------------------------------------------
    # [2] Temperature zones
    # ------------------------------------------------------------------
    banner("Temperature zones time-series", 2, 10)
    try:
        from plot_timeseries import plot_temperature_zones
        files = plot_temperature_zones(args.input, args.out, verbose=args.verbose)
        generated += files
        if not files:
            warnings.append("temperature_zones.csv missing — temp zones plot skipped")
        elif args.verbose:
            print(f"    Generated {len(files)} file(s).")
    except Exception as exc:
        warnings.append(f"Temperature zones failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [3] Streamfunction (max|Ψ| + heatmap)
    # ------------------------------------------------------------------
    banner("Streamfunction diagnostics", 3, 10)
    try:
        from plot_timeseries import plot_max_abs_psi
        files = plot_max_abs_psi(args.input, args.out, verbose=args.verbose)
        generated += files
        if not files:
            warnings.append("streamfunction_summary.csv missing — max|Ψ| plot skipped")
    except Exception as exc:
        warnings.append(f"max|Ψ| plot failed: {exc}")
        print(f"  [ERROR] {exc}")

    try:
        from plot_heatmaps import plot_streamfunction
        files = plot_streamfunction(args.input, args.out, verbose=args.verbose)
        generated += files
        if not files:
            warnings.append("streamfunction_step_*.csv missing — SF heatmap skipped")
    except Exception as exc:
        warnings.append(f"SF heatmap failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [4] Water balance
    # ------------------------------------------------------------------
    banner("Water-balance panels", 4, 10)
    try:
        from plot_moisture import plot_water_balance
        files = plot_water_balance(args.input, args.out, verbose=args.verbose)
        generated += files
        if not files:
            warnings.append("moisture_balance.csv missing — water balance plot skipped")
        elif args.verbose:
            print(f"    Generated {len(files)} file(s).")
    except Exception as exc:
        warnings.append(f"Water balance failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [5] Evaporation & condensation
    # ------------------------------------------------------------------
    banner("Evaporation & condensation time-series", 5, 10)
    try:
        from plot_moisture import plot_evap_cond
        files = plot_evap_cond(args.input, args.out, verbose=args.verbose)
        generated += files
        if not files:
            warnings.append("evap/cond log files missing — evap/cond plot skipped")
        elif args.verbose:
            print(f"    Generated {len(files)} file(s).")
    except Exception as exc:
        warnings.append(f"Evap/cond plot failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [6] Altitude temperature profile + simulation energy
    # ------------------------------------------------------------------
    banner("Altitude–temperature profile & energy", 6, 10)
    try:
        from plot_timeseries import plot_altitude_temperature, plot_simulation_energy
        generated += plot_altitude_temperature(args.input, args.out, verbose=args.verbose)
        generated += plot_simulation_energy(args.input, args.out, verbose=args.verbose)
    except Exception as exc:
        warnings.append(f"Alt/temp or energy plot failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [7] Particle heatmaps (v_theta, moisture)
    # ------------------------------------------------------------------
    banner("Particle-derived heatmaps (v_theta, moisture)", 7, 10)
    try:
        from plot_heatmaps import plot_vtheta_heatmap, plot_temperature_lat_alt
        files = plot_vtheta_heatmap(args.input, args.out,
                                    max_particles=args.max_particles,
                                    verbose=args.verbose)
        generated += files
        if not files:
            # Only warn if the source file is actually absent
            if not inv.get("circulation_accum") and not inv.get("particle_spherical"):
                warnings.append("circulation_accum and particle_spherical not found — v_theta heatmap skipped")
            else:
                warnings.append("v_theta heatmap skipped — check verbose output for column details")
    except Exception as exc:
        warnings.append(f"v_theta heatmap failed: {exc}")
        print(f"  [ERROR] {exc}")

    try:
        from plot_moisture import plot_humidity_heatmaps
        files = plot_humidity_heatmaps(args.input, args.out,
                                       max_particles=args.max_particles,
                                       verbose=args.verbose)
        generated += files
        if not files:
            if not inv.get("particle_spherical"):
                warnings.append("particle_spherical_step_*.csv not found — moisture heatmaps skipped")
            else:
                warnings.append("Moisture heatmaps skipped — check missing_required_outputs.md for details")
    except Exception as exc:
        warnings.append(f"Moisture heatmaps failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [8] 3D particle viewers
    # ------------------------------------------------------------------
    banner("3D particle shell viewers", 8, 10)
    try:
        from plot_particles_3d import plot_3d_viewers
        files = plot_3d_viewers(args.input, args.out,
                                max_particles=args.max_particles,
                                verbose=args.verbose)
        generated += files
        if not files:
            warnings.append("No particle snapshot file — 3D viewers skipped")
    except Exception as exc:
        warnings.append(f"3D viewers failed: {exc}")
        print(f"  [ERROR] {exc}")

    # ------------------------------------------------------------------
    # [9] Particle animations
    # ------------------------------------------------------------------
    banner("Particle animations", 9, 10)
    try:
        from animation_builder import build_particle_animations
        files = build_particle_animations(
            args.input, args.out,
            max_particles=min(args.max_particles, 2000),
            skip_animation=args.skip_animation,
            verbose=args.verbose,
        )
        generated += files
        if not files and not args.skip_animation:
            warnings.append("No particle snapshot files — animations skipped")
    except Exception as exc:
        warnings.append(f"Animation build failed: {exc}")
        print(f"  [ERROR] {exc}")

    # Load moisture summaries (needed for validation report)
    wb_summary = load_json_summary(
        os.path.join(args.out, "summary", "water_balance_summary.json")
    )
    ec_summary = load_json_summary(
        os.path.join(args.out, "summary", "evap_cond_summary.json")
    )

    # ------------------------------------------------------------------
    # [9b] Copy validation CSVs and write markdown summaries
    # ------------------------------------------------------------------
    banner("Validation reports", 10, 11)
    generated += _copy_validation_files(args.input, args.out,
                                        wb_summary=wb_summary,
                                        verbose=args.verbose)

    # ------------------------------------------------------------------
    # [9c] ASCII VTK export for ParaView
    # ------------------------------------------------------------------
    banner("VTK export (ASCII legacy)", 11, 12)
    try:
        generated += _write_vtk_particles(args.input, args.out, verbose=args.verbose)
    except Exception as exc:
        warnings.append(f"VTK export failed: {exc}")
        print(f"  [ERROR] VTK export: {exc}")

    # ------------------------------------------------------------------
    # [10] Dashboard summary JSON + manifest
    # ------------------------------------------------------------------
    banner("Dashboard summary & manifest update", 12, 12)

    # Detect latest simulation step from simulation_log.csv
    latest_step: Any = None
    sim_log = os.path.join(args.input, "simulation_log.csv")
    if os.path.isfile(sim_log):
        try:
            import pandas as _pd
            sl = _pd.read_csv(sim_log)
            if "step" in sl.columns and not sl.empty:
                latest_step = int(sl["step"].iloc[-1])
        except Exception:
            pass

    # Total particle count from latest snapshot CSV (header excluded)
    particle_total_count: Optional[int] = None
    for _pat in ("particle_spherical_step_*.csv", "particles_step_*.csv"):
        _snap = find_latest_file(args.input, _pat)
        if _snap and os.path.isfile(_snap):
            try:
                with open(_snap, encoding="utf-8", errors="replace") as _pf:
                    particle_total_count = max(0, sum(1 for _ in _pf) - 1)
            except OSError:
                pass
            break

    # Collect all HTML / PNG / report / animation counts
    def _count_by_ext(out_dir: str, subdir: str, ext: str) -> int:
        d = os.path.join(out_dir, subdir)
        if not os.path.isdir(d):
            return 0
        return sum(1 for f in os.listdir(d) if f.endswith(ext))

    n_html      = _count_by_ext(args.out, "html",           ".html")
    n_png       = _count_by_ext(args.out, "png",            ".png")
    n_report    = _count_by_ext(args.out, "report_figures", ".png")
    n_animation = (_count_by_ext(args.out, "animations", ".gif") +
                   _count_by_ext(args.out, "animations", ".png"))

    # -- Availability flags (resolved against actual generated files) --
    gen_set = set(generated)
    def _exists_in(substr: str) -> bool:
        return any(substr in f for f in gen_set if os.path.isfile(f))

    strmfn_avail  = _exists_in("streamfunction")
    viewer_avail  = _exists_in("particle_3d")
    stage4_avail  = (
        _exists_in("water_balance") or
        _exists_in("evap_cond") or
        _exists_in("humidity_heatmap") or
        _exists_in("specific_humidity") or
        _exists_in("relative_humidity") or
        _exists_in("q_p")
    )

    # Prune stale auto-generated warnings that are now resolved by actual output
    resolved_keywords = []
    if strmfn_avail:
        resolved_keywords += ["streamfunction"]
    if viewer_avail:
        resolved_keywords += ["particle_3d", "3d viewer"]
    if stage4_avail:
        resolved_keywords += ["moisture", "q_p", "water balance"]
    active_warnings = [
        w for w in warnings
        if not any(kw in w.lower() for kw in resolved_keywords)
    ]

    summary_data: Dict[str, Any] = {
        "generated_at":              datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_folder":              os.path.abspath(args.input),
        "latest_step_detected":      latest_step,
        "particle_total_count":      particle_total_count,
        "counts": {
            "html":        n_html,
            "png":         n_png,
            "report_figs": n_report,
            "animations":  n_animation,
        },
        "waterBalance":              wb_summary,
        "evaporationCondensation":   ec_summary,
        "warnings":                  active_warnings,
        "missing_optional_files":    [w for w in active_warnings if "missing" in w.lower()],
        "stage3_outputs_available":  len(generated) > 0,
        "stage4_outputs_available":  stage4_avail,
        "streamfunction_available":  strmfn_avail,
        "particle_viewer_available": viewer_avail,
        "latestStep":                latest_step,
    }

    # Write dashboard_summary.json
    dash_json = os.path.join(args.out, "summary", "dashboard_summary.json")
    with open(dash_json, "w", encoding="utf-8") as fh:
        json.dump(summary_data, fh, indent=2, default=str)
    generated.append(dash_json)
    print(f"  [OK] {os.path.relpath(dash_json)}")

    # Update manifest
    js_path = build_manifest(
        args.out,
        summary_data=summary_data,
        warnings_list=warnings,
        verbose=args.verbose,
    )
    generated.append(js_path)
    print(f"  [OK] {os.path.relpath(js_path)}")
    print(f"       {len([a for a in generated if a])} total files generated in this run.")

    # Print per-step report
    print(f"\n  Water balance  : {wb_summary.get('recommended_status', 'NOT_AVAILABLE')}")
    if latest_step:
        print(f"  Latest step    : {latest_step:,}")

    # ------------------------------------------------------------------
    # Print full footer and optionally open browser
    # ------------------------------------------------------------------
    footer(generated, warnings, t0, args.out)

    if args.open_dashboard:
        idx = os.path.join(args.out, "index.html")
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", idx], check=False)
            elif platform.system() == "Windows":
                os.startfile(idx)   # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", idx], check=False)
        except Exception as exc:
            print(f"  [WARN] Could not open browser: {exc}")


if __name__ == "__main__":
    main()
