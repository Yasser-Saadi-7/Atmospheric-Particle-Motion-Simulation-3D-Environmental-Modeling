"""
data_loader.py — Stage UI-3
==========================================================
Shared data-loading utilities for the AtmosphericSimulation
visualization pipeline.  No heavy logic here — just clean I/O
helpers, column-alias resolution, and small utilities.

Import pattern (sibling modules or build_dashboard.py):
    from data_loader import read_csv_safe, get_column, ...
==========================================================
"""

import os
import re
import glob
from pathlib import Path
from typing import Optional, List

# pandas and numpy are imported lazily inside the functions that need them.
# Stdlib-only helpers (find_step_files, ensure_output_dirs, set_mpl_style …)
# can be imported safely even when the scientific packages are not installed.


# ------------------------------------------------------------------
# Column alias map
# Maps a canonical key → list of possible column names in the CSV.
# choose_column() / get_column() scan this list left-to-right.
# ------------------------------------------------------------------

COLUMN_ALIASES: dict = {
    # Position (Cartesian)
    "x":           ["x", "pos_x", "r_x", "X"],
    "y":           ["y", "pos_y", "r_y", "Y"],
    "z":           ["z", "pos_z", "r_z", "Z"],
    # Velocity (Cartesian)
    "vx":          ["vx", "v_x", "vel_x"],
    "vy":          ["vy", "v_y", "vel_y"],
    "vz":          ["vz", "v_z", "vel_z"],
    # Thermodynamics — includes 'temperature' column name from particle_spherical files
    "T_p":         ["T_p", "Tp", "temperature", "temp", "T",
                    "kinetic_temperature", "temp_K",
                    "mean_temperature", "mean_T", "T_kinetic"],
    # Humidity
    "q_p":         ["q_p", "specificHumidity", "specific_humidity",
                    "humidity", "specific_humidity_q", "q"],
    "q_sat":       ["q_sat", "qsat", "saturation_humidity",
                    "q_sat_approx", "humidity_sat"],
    "relative_humidity": ["relative_humidity", "RH", "rh", "rel_hum"],
    # ---- Spherical coordinates (broad aliases cover real CSV column names) ----
    "radius":      ["r", "radius", "r_sph"],
    # altitude: includes names used in pre-binned grid files
    "altitude":    ["altitude", "alt", "h", "height",
                    "altitude_center", "alt_center", "altitude_bin",
                    "altitude_center_km"],
    # latitude: includes names used in grid and spherical files
    "latitude":    ["latitude", "lat",
                    "latitude_center_deg", "lat_center", "latitude_deg",
                    "theta_deg", "lat_deg",
                    "theta", "latitude_bin"],
    "longitude":   ["longitude", "lon", "phi", "lon_deg", "phi_deg"],
    "v_r":         ["v_r", "vr", "radial_velocity", "vel_r"],
    # v_theta: includes mean_v_theta used in circulation_accum files
    "v_theta":     ["v_theta", "vtheta", "v_lat", "meridional_velocity",
                    "mean_v_theta", "vtheta_mean", "vel_theta"],
    "v_phi":       ["v_phi", "vphi", "v_lon", "zonal_velocity",
                    "mean_v_phi", "vel_phi"],
    # ---- Streamfunction (covers all known column name variants) ----
    "psi":         ["psi", "Psi", "PSI", "streamfunction", "stream_function",
                    "psi_value", "strmfn"],
    "max_abs_psi": ["max_abs_psi", "max_psi_abs", "max_abs_psi_value"],
    "min_psi":     ["min_psi", "psi_min"],
    "max_psi":     ["max_psi", "psi_max"],
    # Lat / alt as used in grid-based heatmap files (aliases mirror latitude/altitude)
    "lat":         ["lat", "latitude",
                    "latitude_center_deg", "lat_center", "latitude_deg",
                    "theta_deg", "lat_deg", "theta", "latitude_bin"],
    "alt":         ["alt", "altitude", "h", "height",
                    "altitude_center", "alt_center", "altitude_bin",
                    "altitude_center_km"],
    # ---- Time ----
    "step":        ["step", "Step", "time_step", "sim_step"],
    # ---- Water balance ----
    "total_q":     ["total_q", "totalHumidity", "sum_q"],
    "expected_total_q": ["expected_total_q", "expected_q"],
    "water_balance_error": ["water_balance_error", "error", "wb_error"],
    "water_balance_relative_error": [
        "water_balance_relative_error", "relative_error", "rel_error",
        "wb_rel_error",
    ],
    "cumulative_evaporation": [
        "cumulative_evaporation", "cum_evaporation", "cum_evap",
    ],
    "cumulative_condensation": [
        "cumulative_condensation", "cum_condensation", "cum_cond",
    ],
    # ---- Evaporation ----
    "evaporation_this_step": [
        "evaporation_this_step", "evap_this_step", "evaporation_rate",
    ],
    # ---- Condensation ----
    "condensation_this_step": [
        "condensation_this_step", "cond_this_step", "condensation_rate",
    ],
    "latent_heating_this_step": [
        "latent_heating_this_step", "latent_heat_this_step", "latent_rate",
    ],
    "cumulative_latent_heating": [
        "cumulative_latent_heating", "cum_latent_heating", "cum_lh",
    ],
    # ---- Temperature zones ----
    "temp_equatorial": [
        "temp_equatorial", "T_equatorial", "temp_eq_0_30", "equatorial",
    ],
    "temp_midlatitude": [
        "temp_midlatitude", "T_mid", "temp_mid_30_60", "midlatitude",
    ],
    "temp_polar": [
        "temp_polar", "T_polar", "temp_polar_60_90", "polar",
    ],
    # ---- Energetics (simulation_log) ----
    "e_kin":  ["e_kin", "KE", "kinetic_energy"],
    "e_grav": ["e_grav", "PE", "potential_energy"],
    "e_total":["e_total", "E_total", "total_energy"],
    # ---- Additional grid fields ----
    "samples":     ["samples", "count", "n_samples", "n_particles"],
    "mean_mass_flux": ["mean_mass_flux", "mass_flux", "mean_flux"],
}


# ------------------------------------------------------------------
# File finders
# ------------------------------------------------------------------

def find_latest_file(input_dir: str, pattern: str) -> Optional[str]:
    """
    Return the file with the highest *numeric* step number matching
    glob `pattern` inside `input_dir`, or None if no match.

    Uses extract_step_from_filename() for sorting so that
    step_100000.csv correctly beats step_95000.csv even though
    '1' < '9' lexicographically.
    """
    matches = glob.glob(os.path.join(input_dir, pattern))
    if not matches:
        return None
    return max(matches, key=extract_step_from_filename)


def find_step_files(input_dir: str, pattern: str) -> List[str]:
    """Return all files matching `pattern` in `input_dir`, sorted by numeric step."""
    matches = glob.glob(os.path.join(input_dir, pattern))
    return sorted(matches, key=extract_step_from_filename)


def extract_step_from_filename(filename: str) -> int:
    """
    Extract the first run of digits from the basename.
    E.g. 'particles_step_050000.csv' → 50000.
    """
    match = re.search(r"(\d+)", os.path.basename(filename))
    return int(match.group(1)) if match else 0


# ------------------------------------------------------------------
# CSV I/O
# ------------------------------------------------------------------

def read_csv_safe(path: str):
    """
    Read a CSV, returning None (and printing a warning) on any error.
    Also returns None for empty files.
    Imports pandas lazily so the module loads even without pandas installed.
    """
    if not os.path.isfile(path):
        return None
    try:
        import pandas as pd  # lazy import
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except ImportError:
        raise  # let caller handle missing pandas
    except Exception as exc:  # noqa: BLE001
        print(f"  [WARN] Could not read '{path}': {exc}")
        return None


def normalize_columns(df):
    """Strip whitespace from all column names (do NOT lowercase — preserves T_p etc.)."""
    df.columns = [c.strip() for c in df.columns]
    return df


# ------------------------------------------------------------------
# Column resolution
# ------------------------------------------------------------------

def choose_column(df, aliases: List[str]) -> Optional[str]:
    """
    Return the first column name in `df` that appears in `aliases`.
    Matching is case-insensitive as a fallback.
    """
    for alias in aliases:
        if alias in df.columns:
            return alias
    # Case-insensitive fallback
    lower_map = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    return None


def get_column(df, key: str) -> Optional[str]:
    """
    Return the actual DataFrame column name for the canonical `key`,
    looking up COLUMN_ALIASES.  Returns None if not found.
    """
    aliases = COLUMN_ALIASES.get(key, [key])
    return choose_column(df, aliases)


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def ensure_output_dirs(out_dir: str) -> None:
    """Create all required output subdirectories under `out_dir`."""
    for sub in ("html", "png", "report_figures", "animations",
                "summary", "validation", "vtk", "docs", "assets"):
        Path(os.path.join(out_dir, sub)).mkdir(parents=True, exist_ok=True)


def report_csv_columns(path: str, label: str, verbose: bool = False) -> List[str]:
    """
    Read just the header of a CSV and return the column list.
    Prints them when verbose=True.  Returns [] on failure.
    """
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n")
        cols = [c.strip() for c in header.split(",")]
        if verbose:
            print(f"    Columns in {label} ({os.path.basename(path)}):")
            print(f"      {', '.join(cols)}")
        return cols
    except Exception as exc:  # noqa: BLE001
        if verbose:
            print(f"    [WARN] Could not read header of {path}: {exc}")
        return []


def check_required_columns(
    cols: List[str],
    required_keys: List[str],
    label: str,
    verbose: bool = False,
) -> dict:
    """
    For each key in required_keys, check whether any alias resolves against
    the given column list.  Returns a dict {key: found_col or None}.
    Prints a clear per-key found/missing line when verbose=True.
    """
    result = {}
    fake_df_cols = cols  # we'll do a string-match without a real DataFrame
    for key in required_keys:
        aliases = COLUMN_ALIASES.get(key, [key])
        found = None
        # check exact match first, then case-insensitive
        for alias in aliases:
            if alias in cols:
                found = alias
                break
        if found is None:
            lower_map = {c.lower(): c for c in cols}
            for alias in aliases:
                if alias.lower() in lower_map:
                    found = lower_map[alias.lower()]
                    break
        result[key] = found
        if verbose:
            if found:
                print(f"      {key:25s} → '{found}'")
            else:
                print(f"      {key:25s} → MISSING  (tried: {', '.join(aliases[:4])}…)")
    return result


def downsample_dataframe(
    df,
    max_rows: int,
    random_state: int = 42,
):
    """
    Deterministically downsample a pandas DataFrame to at most `max_rows` rows.
    Returns the original DataFrame unchanged if it is already small enough.
    """
    if len(df) <= max_rows:
        return df
    return df.sample(n=max_rows, random_state=random_state).reset_index(drop=True)


def set_mpl_style() -> None:
    """Apply a clean, professional matplotlib style (call once per module)."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor":   "white",
        "axes.facecolor":     "#f8f9fa",
        "axes.grid":          True,
        "grid.color":         "#dee2e6",
        "grid.linestyle":     "-",
        "grid.linewidth":     0.6,
        "grid.alpha":         0.8,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "font.family":        "DejaVu Sans",
        "font.size":          10,
        "axes.titlesize":     12,
        "axes.titleweight":   "bold",
        "axes.labelsize":     10,
        "xtick.labelsize":    9,
        "ytick.labelsize":    9,
        "legend.fontsize":    9,
        "legend.framealpha":  0.85,
        "figure.dpi":         100,
    })


# Colour palette used consistently across all modules
PALETTE = {
    "equatorial": "#e74c3c",
    "midlatitude": "#27ae60",
    "polar":       "#3498db",
    "total_q":     "#2980b9",
    "expected_q":  "#e74c3c",
    "evap":        "#27ae60",
    "cond":        "#8e44ad",
    "latent":      "#e67e22",
    "error":       "#c0392b",
    "rel_error":   "#d35400",
    "psi":         "#6c3483",
    "vtheta":      "#154360",
    "navy":        "#0d1b2a",
    "cyan":        "#17a2b8",
}
