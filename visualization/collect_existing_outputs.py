#!/usr/bin/env python3
"""
Stage UI-2: collect_existing_outputs.py
================================================================
Scans the AtmosphericSimulation project for existing visualization
artifacts, copies them into standardized visualization_output/
subdirectories, and generates a JavaScript manifest file for the
static dashboard.

Usage:
    python3 visualization/collect_existing_outputs.py

Requirements:
    Python 3.7+, standard library only.
    No external packages required (no pandas, numpy, matplotlib, etc.).

What this script does:
    1. Creates the full visualization_output/ subdirectory structure.
    2. Scans all recognized source directories for visualization artifacts.
    3. Copies found files into their canonical destination paths.
    4. Generates visualization_output/assets/generated_manifest.js — a
       JavaScript file that sets window.DASHBOARD_MANIFEST, consumed by
       the static dashboard without any server or fetch() call.
    5. Prints a concise summary of found/missing/copied files.
================================================================
"""

import os
import sys
import shutil
import json
import fnmatch
from datetime import datetime, timezone
from pathlib import Path

# ----------------------------------------------------------------
# Paths
# ----------------------------------------------------------------

SCRIPT_DIR    = Path(__file__).resolve().parent          # .../visualization/
PROJECT_ROOT  = SCRIPT_DIR.parent                        # .../AtmosphericSimulation/
VIZDASH_DIR   = PROJECT_ROOT / "visualization_output"    # destination root
MANIFEST_PATH = VIZDASH_DIR / "assets" / "generated_manifest.js"

# ----------------------------------------------------------------
# Output subdirectory structure to create / maintain
# ----------------------------------------------------------------

OUTPUT_SUBDIRS = [
    "png", "html", "animations", "report_figures",
    "validation", "summary", "vtk", "docs",
]

# ----------------------------------------------------------------
# Source scan directories (relative to PROJECT_ROOT).
# visualization_output/ is deliberately excluded to prevent self-copies.
# ----------------------------------------------------------------

SCAN_DIRS_REL = [
    ".",           # project root — catches README.md, etc.
    "output",      # simulation CSV output
    "visualization",  # peer script directory
    "docs",        # physics_model_report.md
    "png",         # pre-existing figures (if any)
    "html",        # pre-existing interactive plots (if any)
    "animations",  # pre-existing animations (if any)
    "report_figures",
    "validation",
    "summary",
    "vtk",
]

# Directory names to never descend into
EXCLUDE_DIRS = frozenset({
    "build", ".git", "__pycache__", "node_modules",
    "venv", ".venv", "env", ".env",
    "visualization_output",
})

# Maximum file size to copy (50 MB — skip huge unrelated binaries)
MAX_FILE_BYTES = 50 * 1024 * 1024

# ----------------------------------------------------------------
# Recognized file extension → default destination subdirectory
# ----------------------------------------------------------------

EXT_TO_SUBDIR = {
    ".png":  "png",
    ".jpg":  "png",
    ".jpeg": "png",
    ".gif":  "animations",
    ".html": "html",
    ".mp4":  "animations",
    ".md":   "docs",
    ".txt":  "validation",
    ".csv":  "summary",
    ".json": "summary",
    ".vtu":  "vtk",
    ".vtk":  "vtk",
}

# ----------------------------------------------------------------
# Artifact Registry
# Each entry: (filename, category, dest_subdir, title, description)
# category must match a key in the manifest's artifacts object.
# ----------------------------------------------------------------

ARTIFACT_REGISTRY = [
    # ---- Streamfunction ----
    ("streamfunction_heatmap_contours.png",
     "streamfunction", "png",
     "Streamfunction heatmap",
     "Latitude-altitude streamfunction diagnostic (preview PNG)."),
    ("streamfunction_heatmap_contours_300dpi.png",
     "streamfunction", "report_figures",
     "Streamfunction heatmap (300 DPI)",
     "Latitude-altitude streamfunction diagnostic (report-ready PNG)."),
    ("streamfunction_heatmap_contours.html",
     "streamfunction", "html",
     "Streamfunction heatmap (interactive)",
     "Interactive Plotly streamfunction heatmap with contours."),
    ("max_abs_psi_vs_time.png",
     "streamfunction", "png",
     "Max |Psi| vs time",
     "Maximum absolute streamfunction value over simulation time (preview)."),
    ("max_abs_psi_vs_time_300dpi.png",
     "streamfunction", "report_figures",
     "Max |Psi| vs time (300 DPI)",
     "Maximum absolute streamfunction over time (report-ready)."),
    ("max_abs_psi_vs_time.html",
     "streamfunction", "html",
     "Max |Psi| vs time (interactive)",
     "Interactive time-series of max |Psi|."),

    # ---- Meridional wind ----
    ("vtheta_heatmap.png",
     "meridionalWind", "png",
     "Meridional wind heatmap",
     "Mean meridional wind v_theta in latitude-altitude coordinates (preview)."),
    ("vtheta_heatmap_300dpi.png",
     "meridionalWind", "report_figures",
     "Meridional wind heatmap (300 DPI)",
     "Mean meridional wind v_theta (report-ready)."),
    ("vtheta_heatmap.html",
     "meridionalWind", "html",
     "Meridional wind heatmap (interactive)",
     "Interactive mean meridional wind heatmap."),

    # ---- Water balance ----
    ("water_balance_panels.png",
     "waterBalance", "png",
     "Water balance panels",
     "Water conservation: total_q vs expected_total_q (preview PNG)."),
    ("water_balance_panels_300dpi.png",
     "waterBalance", "report_figures",
     "Water balance panels (300 DPI)",
     "Water conservation diagnostics (report-ready)."),
    ("water_balance_panels.html",
     "waterBalance", "html",
     "Water balance panels (interactive)",
     "Interactive water balance diagnostic panels."),
    ("moisture_balance.csv",
     "waterBalance", "summary",
     "Moisture balance data",
     "Per-step: total_q, expected_total_q, water balance error and status."),

    # ---- Evaporation / condensation ----
    ("evap_cond_timeseries.png",
     "evaporationCondensation", "png",
     "Evap/cond time-series",
     "Evaporation and condensation diagnostics (preview PNG)."),
    ("evap_cond_timeseries_300dpi.png",
     "evaporationCondensation", "report_figures",
     "Evap/cond time-series (300 DPI)",
     "Evaporation and condensation diagnostics (report-ready)."),
    ("evap_cond_timeseries.html",
     "evaporationCondensation", "html",
     "Evap/cond time-series (interactive)",
     "Interactive evaporation and condensation time-series."),
    ("evap_cond_rates_only.png",
     "evaporationCondensation", "png",
     "Evap/cond rates",
     "Instantaneous evaporation and condensation rates."),
    ("evap_cond_cumulative_only.png",
     "evaporationCondensation", "png",
     "Evap/cond cumulative",
     "Cumulative evaporation and condensation totals."),
    ("condensation_log.csv",
     "evaporationCondensation", "summary",
     "Condensation log data",
     "Per-step condensation amount, cumulative total, and latent heating."),
    ("evaporation_log.csv",
     "evaporationCondensation", "summary",
     "Evaporation log data",
     "Per-step evaporation amount, cumulative total, and event count."),

    # ---- Particle viewer ----
    ("particle_3d_temperature.html",
     "particleViewer", "html",
     "3D viewer: temperature",
     "Interactive 3D particle shell colored by temperature."),
    ("particle_3d_vr.html",
     "particleViewer", "html",
     "3D viewer: radial velocity",
     "Interactive 3D particle shell colored by radial velocity."),
    ("particle_3d_vtheta.html",
     "particleViewer", "html",
     "3D viewer: meridional velocity",
     "Interactive 3D particle shell colored by meridional velocity."),
    ("particle_3d_qp.html",
     "particleViewer", "html",
     "3D viewer: specific humidity",
     "Interactive 3D particle shell colored by specific humidity."),
    ("particle_3d_relative_humidity.html",
     "particleViewer", "html",
     "3D viewer: relative humidity",
     "Interactive 3D particle shell colored by relative humidity."),

    # ---- Particle animations ----
    ("particle_animation_preview.gif",
     "particleAnimations", "animations",
     "Particle animation preview (GIF)",
     "Animated particle shell evolution (GIF format)."),
    ("particle_animation_preview.png",
     "particleAnimations", "animations",
     "Particle animation preview (PNG)",
     "Static preview frame from particle animation."),
    ("particle_animation_temperature.html",
     "particleAnimations", "html",
     "Particle animation: temperature",
     "Interactive particle animation colored by temperature."),
    ("particle_animation_qp.html",
     "particleAnimations", "html",
     "Particle animation: specific humidity",
     "Interactive particle animation colored by specific humidity."),
    ("particle_animation_vr.html",
     "particleAnimations", "html",
     "Particle animation: radial velocity",
     "Interactive particle animation colored by radial velocity."),

    # ---- Moisture ----
    ("humidity_lat_alt_heatmap.png",
     "moisture", "png",
     "Humidity heatmap",
     "Specific humidity q_p in latitude-altitude coordinates (preview)."),
    ("humidity_lat_alt_heatmap_300dpi.png",
     "moisture", "report_figures",
     "Humidity heatmap (300 DPI)",
     "Specific humidity q_p (report-ready)."),
    ("relative_humidity_heatmap.png",
     "moisture", "png",
     "Relative humidity heatmap",
     "Relative humidity in latitude-altitude coordinates (preview)."),
    ("relative_humidity_heatmap_300dpi.png",
     "moisture", "report_figures",
     "Relative humidity heatmap (300 DPI)",
     "Relative humidity (report-ready)."),
    ("condensation_zones_heatmap.png",
     "moisture", "png",
     "Condensation zones heatmap",
     "Condensation zone locations in latitude-altitude coordinates."),
    ("condensation_overlay_on_psi.png",
     "moisture", "png",
     "Condensation overlay on Psi",
     "Condensation zones overlaid on streamfunction heatmap."),

    # ---- Thermal diagnostics ----
    ("temperature_zones_timeseries.png",
     "thermalDiagnostics", "png",
     "Temperature zones time-series",
     "Equatorial, mid-latitude, and polar temperature zones (preview)."),
    ("temperature_zones_timeseries_300dpi.png",
     "thermalDiagnostics", "report_figures",
     "Temperature zones time-series (300 DPI)",
     "Temperature zone diagnostics (report-ready)."),
    ("temperature_lat_alt_heatmap.png",
     "thermalDiagnostics", "png",
     "Temperature lat-alt heatmap",
     "Latitude-altitude temperature field heatmap."),
    ("radial_velocity_snapshot.png",
     "thermalDiagnostics", "png",
     "Radial velocity snapshot",
     "Radial velocity field snapshot."),
    ("temperature_zones.csv",
     "thermalDiagnostics", "summary",
     "Temperature zones data",
     "Per-step equatorial, mid-latitude, and polar temperature values."),
    ("simulation_log.csv",
     "thermalDiagnostics", "summary",
     "Simulation log data",
     "General simulation state: particle count, radii, energy components."),

    # ---- Validation ----
    ("full_validation_report.md",
     "validation", "validation",
     "Full validation report",
     "PASS/WARNING/FAIL validation report across all simulation stages."),
    ("stage4_validation_report.md",
     "validation", "validation",
     "Stage 4 validation report",
     "Moisture stage PASS/WARNING/FAIL validation report."),
    ("validation_report.md",
     "validation", "validation",
     "Validation report",
     "General PASS/WARNING/FAIL validation report."),
    ("checks_table.csv",
     "validation", "validation",
     "Validation checks table",
     "Tabular PASS/WARNING/FAIL results from validation pipeline."),
    ("final_metrics.csv",
     "validation", "summary",
     "Final metrics CSV",
     "Summary metrics from the completed simulation run."),
    ("final_validation_summary.json",
     "validation", "summary",
     "Final validation summary (JSON)",
     "JSON-format final validation summary for programmatic use."),
    ("dashboard_summary.json",
     "validation", "summary",
     "Dashboard summary (JSON)",
     "Machine-readable dashboard summary."),

    # ---- Documentation ----
    ("physics_model_report.md",
     "documentation", "docs",
     "Physics model report",
     "Detailed physics model documentation generated from source inspection."),
    ("README.md",
     "documentation", "docs",
     "Project README",
     "Project overview, build instructions, and usage guide."),
    ("README.html",
     "documentation", "docs",
     "Project README (HTML)",
     "HTML-formatted project README."),
]

# Files that should never be copied generically (build/config files that
# happen to share a recognized extension such as .txt)
NEVER_COPY_GENERIC = frozenset({
    "CMakeLists.txt", "Makefile", "makefile", "GNUmakefile",
    ".gitignore", ".gitattributes", "LICENSE", "LICENSE.txt",
    "requirements.txt", "setup.py", "setup.cfg", "pyproject.toml",
    "package.json", "package-lock.json", "yarn.lock",
})

# VTK filename glob patterns (handled separately, matched dynamically)
VTK_PATTERNS = [
    "frame_*.vtu",
    "frame_*.vtk",
    "coarse_grid_*.vtu",
    "coarse_grid_*.vtk",
]

# All manifest category keys (order controls JS object key order)
MANIFEST_CATEGORIES = [
    "streamfunction",
    "meridionalWind",
    "waterBalance",
    "evaporationCondensation",
    "particleViewer",
    "particleAnimations",
    "moisture",
    "thermalDiagnostics",
    "validation",
    "reportFigures",
    "vtk",
    "documentation",
]

# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def make_artifact_id(filename: str) -> str:
    """Derive a JS-safe identifier from a filename."""
    stem = Path(filename).stem
    result = []
    for ch in stem.lower():
        result.append(ch if ch.isalnum() else "_")
    return "".join(result)


def should_copy(src: Path, dst: Path) -> bool:
    """True when src should be copied to dst (dst absent or src is newer)."""
    if not dst.exists():
        return True
    return src.stat().st_mtime > dst.stat().st_mtime


def try_copy(src: Path, dst: Path, stats: dict) -> bool:
    """
    Copy src → dst if needed.
    Returns True if the file was actually written.
    Updates stats dict in place.
    """
    if src.resolve() == dst.resolve():
        # Same physical file — skip silently
        stats["skipped"] += 1
        return False
    if not should_copy(src, dst):
        stats["skipped"] += 1
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        stats["copied"] += 1
        rel_src = _rel(src)
        rel_dst = _rel(dst)
        print(f"    [COPY]  {rel_src}  →  {rel_dst}")
        return True
    except OSError as exc:
        print(f"    [WARN]  Could not copy {src}: {exc}", file=sys.stderr)
        stats["errors"] += 1
        return False


def _rel(path: Path) -> str:
    """Return path relative to PROJECT_ROOT, falling back to absolute."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


# ----------------------------------------------------------------
# Scanner
# ----------------------------------------------------------------

def scan_source_dirs() -> dict:
    """
    Walk all SCAN_DIRS_REL (excluding EXCLUDE_DIRS and visualization_output/)
    and return a mapping:
        lowercase_filename  →  list[Path]   (first entry = preferred source)
    """
    found: dict[str, list[Path]] = {}
    viz_resolved = VIZDASH_DIR.resolve()

    for rel in SCAN_DIRS_REL:
        scan_root = (PROJECT_ROOT / rel).resolve()
        if not scan_root.is_dir():
            continue
        # Skip if this scan dir IS visualization_output (shouldn't happen,
        # but guard anyway)
        if scan_root == viz_resolved:
            continue

        for dirpath_str, dirnames, filenames in os.walk(scan_root):
            dirpath = Path(dirpath_str)

            # Prune excluded directories and anything inside visualization_output/
            dirnames[:] = [
                d for d in dirnames
                if d not in EXCLUDE_DIRS
                and (dirpath / d).resolve() != viz_resolved
                and not str((dirpath / d).resolve()).startswith(str(viz_resolved) + os.sep)
            ]

            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext not in EXT_TO_SUBDIR:
                    continue
                fpath = dirpath / fname
                try:
                    size = fpath.stat().st_size
                except OSError:
                    continue
                if size > MAX_FILE_BYTES:
                    continue
                key = fname.lower()
                found.setdefault(key, []).append(fpath)

    return found


# ----------------------------------------------------------------
# Artifact processors
# ----------------------------------------------------------------

def process_registry_artifacts(source_map: dict, stats: dict) -> tuple:
    """
    For each entry in ARTIFACT_REGISTRY:
      - attempt to copy from source_map if dest is absent/stale
      - record whether dest now exists
    Returns (artifact_list, missing_names).
    """
    artifacts = []
    missing_names = []

    for (fname, cat, dest_sub, title, desc) in ARTIFACT_REGISTRY:
        dst = VIZDASH_DIR / dest_sub / fname

        # Attempt copy from source if needed
        if fname.lower() in source_map:
            for src_path in source_map[fname.lower()]:
                try_copy(src_path, dst, stats)
                break   # use first found source

        # Determine existence after potential copy
        exists = dst.exists()
        if not exists:
            missing_names.append(fname)

        artifacts.append({
            "id":           make_artifact_id(fname),
            "title":        title,
            "category":     cat,
            "type":         Path(fname).suffix.lstrip("."),
            "filename":     fname,
            "relativePath": f"{dest_sub}/{fname}",
            "exists":       exists,
            "description":  desc,
        })

    return artifacts, missing_names


def process_vtk_files(source_map: dict, stats: dict) -> list:
    """Find VTK files matching glob patterns and copy them. Returns manifest entries."""
    vtk_dir = VIZDASH_DIR / "vtk"
    entries = []
    seen = set()

    for _key, src_paths in source_map.items():
        for src_path in src_paths:
            fname = src_path.name
            ext   = src_path.suffix.lower()
            if ext not in (".vtu", ".vtk"):
                continue
            if not any(fnmatch.fnmatch(fname, pat) for pat in VTK_PATTERNS):
                continue
            if fname in seen:
                continue
            seen.add(fname)

            dst = vtk_dir / fname
            try_copy(src_path, dst, stats)

            entries.append({
                "id":           make_artifact_id(fname),
                "title":        f"VTK frame: {fname}",
                "category":     "vtk",
                "type":         ext.lstrip("."),
                "filename":     fname,
                "relativePath": f"vtk/{fname}",
                "exists":       dst.exists(),
                "description":  "VTK export file for 3D rendering in ParaView.",
            })

    return entries


def copy_generic_files(source_map: dict, registry_set: set, stats: dict) -> None:
    """
    Copy any recognized file NOT already in the artifact registry
    to its extension-based default destination.
    These files are not tracked in the manifest but are made available
    under visualization_output/ for reference.
    """
    for fname_lower, src_paths in source_map.items():
        if fname_lower in registry_set:
            continue
        for src_path in src_paths:
            # Skip build/config files that happen to have a recognized ext
            if src_path.name in NEVER_COPY_GENERIC:
                continue
            ext = src_path.suffix.lower()
            subdir = EXT_TO_SUBDIR.get(ext)
            if subdir is None:
                continue
            # Only copy generic .txt / .csv / .json files from dedicated
            # data dirs — not from the project root, src/, etc.
            if ext in (".txt", ".csv", ".json"):
                rel_parts = set(src_path.relative_to(PROJECT_ROOT).parts)
                data_dirs = {
                    "output", "validation", "summary",
                    "report_figures", "docs",
                }
                if not rel_parts.intersection(data_dirs):
                    continue
            dst = VIZDASH_DIR / subdir / src_path.name
            try_copy(src_path, dst, stats)
            break   # only copy first found instance


# ----------------------------------------------------------------
# Manifest writer
# ----------------------------------------------------------------

def build_and_write_manifest(artifacts: list, vtk_entries: list) -> dict:
    """
    Group artifacts by category, build the manifest dict, and write
    visualization_output/assets/generated_manifest.js.
    Returns the manifest dict.
    """
    # Group into category buckets
    grouped: dict[str, list] = {cat: [] for cat in MANIFEST_CATEGORIES}

    for art in artifacts:
        cat = art["category"]
        # reportFigures is implied by report_figures subdir artifacts;
        # they are spread across multiple categories so we add them to
        # both their primary category and reportFigures if they're 300dpi
        if cat in grouped:
            grouped[cat].append(art)
        # If a 300dpi file also belongs to reportFigures, add a copy
        if "300dpi" in art["filename"]:
            rf_entry = dict(art)
            rf_entry["category"] = "reportFigures"
            grouped["reportFigures"].append(rf_entry)

    grouped["vtk"].extend(vtk_entries)

    available_count = sum(1 for a in artifacts if a["exists"])
    available_count += sum(1 for v in vtk_entries if v["exists"])
    missing_count   = sum(1 for a in artifacts if not a["exists"])

    manifest = {
        "generatedAt":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "availableCount": available_count,
        "missingCount":   missing_count,
        "isStub":         False,
        "artifacts":      grouped,
        "expected":       [a["filename"] for a in artifacts],
    }

    manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
    js_lines = [
        "/* ================================================================",
        "   generated_manifest.js",
        "   Auto-generated by visualization/collect_existing_outputs.py",
        "   Do NOT edit manually — re-run the script to update.",
        f"   Generated at: {manifest['generatedAt']}",
        "   ================================================================ */",
        "",
        "window.DASHBOARD_MANIFEST = " + manifest_json + ";",
        "",
    ]
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text("\n".join(js_lines), encoding="utf-8")

    return manifest


# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------

def main() -> None:
    print("=" * 65)
    print("  AtmosphericSimulation — Stage UI-2 Output Collector")
    print("=" * 65)
    print(f"  Project root : {PROJECT_ROOT}")
    print(f"  Dashboard    : {VIZDASH_DIR}")
    print()

    # Step 1: Ensure all output subdirectories exist
    print("[1/5] Creating visualization_output/ subdirectories...")
    for sub in OUTPUT_SUBDIRS:
        (VIZDASH_DIR / sub).mkdir(parents=True, exist_ok=True)
    (VIZDASH_DIR / "assets").mkdir(parents=True, exist_ok=True)
    print("      OK — all subdirectories present.")
    print()

    # Step 2: Scan source directories
    print("[2/5] Scanning source directories for recognized files...")
    source_map = scan_source_dirs()
    unique_count = len(source_map)
    print(f"      Found {unique_count} unique filename(s) across source dirs.")
    print()

    # Step 3: Process registry artifacts
    print("[3/5] Processing registry artifacts...")
    stats: dict = {"copied": 0, "skipped": 0, "errors": 0}
    registry_set = {e[0].lower() for e in ARTIFACT_REGISTRY}
    artifacts, missing_names = process_registry_artifacts(source_map, stats)
    print()

    # Step 4: Process VTK files (glob patterns)
    print("[4/5] Processing VTK files (glob patterns)...")
    vtk_entries = process_vtk_files(source_map, stats)
    if vtk_entries:
        print(f"      Found {len(vtk_entries)} VTK file(s).")
    else:
        print("      No VTK files found (expected after Stage UI-3).")

    # Copy any remaining generic recognized files
    copy_generic_files(source_map, registry_set, stats)
    print()

    # Step 5: Generate manifest
    print("[5/5] Generating JavaScript manifest...")
    manifest = build_and_write_manifest(artifacts, vtk_entries)
    print(f"      Manifest written: {_rel(MANIFEST_PATH)}")
    print()

    # ---- Summary ----
    available = manifest["availableCount"]
    missing   = manifest["missingCount"]

    print("=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  Files copied   : {stats['copied']}")
    print(f"  Files skipped  : {stats['skipped']}  (already current)")
    print(f"  Copy errors    : {stats['errors']}")
    print(f"  VTK files      : {len(vtk_entries)}")
    print(f"  Available      : {available}")
    print(f"  Missing        : {missing}")
    print()

    if missing_names:
        print("  Missing (to be generated in Stage UI-3):")
        for name in sorted(missing_names):
            print(f"    \u2012 {name}")
        print()

    print("  Manifest :")
    print(f"    {MANIFEST_PATH}")
    print()
    print("  To open the dashboard:")
    if sys.platform == "win32":
        print(f"    explorer.exe {VIZDASH_DIR / 'index.html'}")
    else:
        print(f"    xdg-open {VIZDASH_DIR / 'index.html'}")
        print(f"    (or: open visualization_output/index.html in any browser)")
    print()
    print("  Next step: Stage UI-3 — generate missing plots and")
    print("             animations from CSV files in output/.")
    print("=" * 65)

    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
