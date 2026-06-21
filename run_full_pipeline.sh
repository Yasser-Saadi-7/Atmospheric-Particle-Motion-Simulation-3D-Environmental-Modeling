#!/usr/bin/env bash
# =============================================================================
# run_full_pipeline.sh
# AtmosphericSimulation — safe, clean, end-to-end pipeline
#
# Key protections:
#   - Uses build/output as the simulation output directory.
#   - Uses the active virtual environment, or project viz_env, automatically.
#   - Verifies Python dependencies before deleting any output.
#   - Never deletes index.html, style.css, or dashboard.js.
#   - Removes only visualization artifacts that can be regenerated.
#   - Supports a visualization-only mode.
#
# Usage examples:
#   bash run_full_pipeline.sh
#   bash run_full_pipeline.sh --visualization-only
#   bash run_full_pipeline.sh --skip-animation
#   bash run_full_pipeline.sh --max-particles 8000
# =============================================================================

set -Eeuo pipefail

# ---- Paths -------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
OUTPUT_DIR="$BUILD_DIR/output"
LEGACY_OUTPUT_DIR="$SCRIPT_DIR/output"

VIZ_SCRIPT="$SCRIPT_DIR/visualization/build_dashboard.py"
VIZ_OUTPUT_DIR="$SCRIPT_DIR/visualization_output"
DISTRIBUTION_BACKUP="$SCRIPT_DIR/distribution/AtmosphericSimulation_Visualization"

DASHBOARD_INDEX="$VIZ_OUTPUT_DIR/index.html"
DASHBOARD_STYLE="$VIZ_OUTPUT_DIR/assets/style.css"
DASHBOARD_JS="$VIZ_OUTPUT_DIR/assets/dashboard.js"
DASHBOARD_MANIFEST="$VIZ_OUTPUT_DIR/assets/generated_manifest.js"

# ---- Defaults ----------------------------------------------------------------
VISUALIZATION_ONLY=false
SKIP_ANIMATION=false
OPEN_DASHBOARD=false
CLEAN_SIMULATION_OUTPUT=true
CLEAN_GENERATED_VISUALIZATIONS=true
MAX_PARTICLES=5000

RUN_MARKER=""

# ---- Terminal formatting -----------------------------------------------------
if [[ -t 1 ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  RESET='\033[0m'
else
  RED=''
  GREEN=''
  YELLOW=''
  CYAN=''
  BOLD=''
  RESET=''
fi

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

cleanup() {
  if [[ -n "${RUN_MARKER:-}" && -f "$RUN_MARKER" ]]; then
    rm -f "$RUN_MARKER"
  fi
}
trap cleanup EXIT

on_error() {
  local code=$?
  error "Pipeline failed at line ${1:-unknown} with exit code $code."
  exit "$code"
}
trap 'on_error $LINENO' ERR

usage() {
  cat <<'EOF'
Usage:
  bash run_full_pipeline.sh [options]

Options:
  --visualization-only
      Use the existing CSV files in build/output.
      Skip CMake configuration, build, and simulation.

  --skip-animation
      Skip GIF/animation generation.

  --open-dashboard
      Pass --open-dashboard to the visualization builder.

  --max-particles N
      Maximum number of particles used for visualization.
      Default: 5000

  --keep-simulation-output
      Do not clean build/output before a full simulation run.
      This may mix old and new CSV files.

  --keep-generated-visualizations
      Do not remove existing generated visualization artifacts.
      index.html, style.css, and dashboard.js are always preserved.

  --help, -h
      Show this help message.
EOF
}

# ---- Parse arguments ---------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --visualization-only)
      VISUALIZATION_ONLY=true
      shift
      ;;
    --skip-animation)
      SKIP_ANIMATION=true
      shift
      ;;
    --open-dashboard)
      OPEN_DASHBOARD=true
      shift
      ;;
    --max-particles)
      if [[ $# -lt 2 || ! "$2" =~ ^[1-9][0-9]*$ ]]; then
        error "--max-particles requires a positive integer."
        exit 2
      fi
      MAX_PARTICLES="$2"
      shift 2
      ;;
    --keep-simulation-output)
      CLEAN_SIMULATION_OUTPUT=false
      shift
      ;;
    --keep-generated-visualizations|--keep-visualization-output)
      CLEAN_GENERATED_VISUALIZATIONS=false
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      error "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
done

# ---- Helpers -----------------------------------------------------------------
select_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s\n' "$PYTHON"
  elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python3" ]]; then
    printf '%s\n' "$VIRTUAL_ENV/bin/python3"
  elif [[ -x "$SCRIPT_DIR/viz_env/bin/python3" ]]; then
    printf '%s\n' "$SCRIPT_DIR/viz_env/bin/python3"
  else
    printf '%s\n' "python3"
  fi
}

check_dependencies() {
  local python_executable="$1"

  info "Checking Python visualization dependencies..."

  if ! "$python_executable" - <<'PY'
import importlib.util
import sys

required = ["numpy", "pandas", "matplotlib", "plotly", "imageio"]
missing = [name for name in required if importlib.util.find_spec(name) is None]

if missing:
    print("Missing packages: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)

import numpy
print("Python:", sys.executable)
print("NumPy:", numpy.__version__)
print("All required visualization packages are available.")
PY
  then
    error "Missing Python visualization dependencies."
    error "Run:"
    error "  cd \"$SCRIPT_DIR\""
    error "  source viz_env/bin/activate"
    if [[ -f "$SCRIPT_DIR/visualization/requirements.txt" ]]; then
      error "  python3 -m pip install -r visualization/requirements.txt"
    else
      error "  python3 -m pip install numpy pandas matplotlib plotly imageio"
    fi
    exit 1
  fi

  success "Python dependencies verified."
}

restore_dashboard_shell() {
  mkdir -p "$VIZ_OUTPUT_DIR/assets"

  if [[ -s "$DASHBOARD_INDEX" &&
        -s "$DASHBOARD_STYLE" &&
        -s "$DASHBOARD_JS" ]]; then
    success "Permanent dashboard shell is available."
    return
  fi

  warn "Permanent dashboard files are missing."
  warn "Attempting restoration from the distribution backup."

  local backup_index="$DISTRIBUTION_BACKUP/index.html"
  local backup_style="$DISTRIBUTION_BACKUP/assets/style.css"
  local backup_js="$DISTRIBUTION_BACKUP/assets/dashboard.js"

  if [[ -s "$backup_index" &&
        -s "$backup_style" &&
        -s "$backup_js" ]]; then
    cp -f "$backup_index" "$DASHBOARD_INDEX"
    cp -f "$backup_style" "$DASHBOARD_STYLE"
    cp -f "$backup_js" "$DASHBOARD_JS"
    success "Dashboard shell restored from distribution backup."
    return
  fi

  error "Could not restore the permanent dashboard shell."
  error "Required files:"
  error "  $DASHBOARD_INDEX"
  error "  $DASHBOARD_STYLE"
  error "  $DASHBOARD_JS"
  exit 1
}

clean_simulation_output() {
  if [[ -z "$OUTPUT_DIR" || "$OUTPUT_DIR" == "/" || "$OUTPUT_DIR" == "$HOME" ]]; then
    error "Unsafe output path: $OUTPUT_DIR"
    exit 1
  fi

  case "$OUTPUT_DIR" in
    "$SCRIPT_DIR"/*) ;;
    *)
      error "Refusing to clean a directory outside the project."
      exit 1
      ;;
  esac

  mkdir -p "$OUTPUT_DIR"

  info "Removing previous simulation output:"
  echo "       $OUTPUT_DIR"

  find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +

  success "Previous simulation output removed."
}

clean_generated_visualizations() {
  mkdir -p "$VIZ_OUTPUT_DIR/assets"

  info "Removing stale generated visualization artifacts..."

  local generated_directories=(
    html
    png
    animations
    report_figures
    summary
    vtk
    validation
  )

  local directory
  for directory in "${generated_directories[@]}"; do
    rm -rf "$VIZ_OUTPUT_DIR/$directory"
  done

  rm -f "$DASHBOARD_MANIFEST"

  success "Generated artifacts removed."
  success "Preserved index.html, style.css, and dashboard.js."
}

verify_existing_csv() {
  shopt -s nullglob
  local files=("$OUTPUT_DIR"/*.csv)
  shopt -u nullglob

  if [[ ${#files[@]} -eq 0 ]]; then
    error "No CSV files were found in $OUTPUT_DIR"
    exit 1
  fi

  success "${#files[@]} CSV file(s) available."
}

verify_fresh_csv() {
  shopt -s nullglob
  local files=("$OUTPUT_DIR"/*.csv)
  shopt -u nullglob

  if [[ ${#files[@]} -eq 0 ]]; then
    error "The simulation did not create CSV files in $OUTPUT_DIR"
    exit 1
  fi

  local fresh_files=()
  local file

  if [[ "$CLEAN_SIMULATION_OUTPUT" == true ]]; then
    fresh_files=("${files[@]}")
  else
    for file in "${files[@]}"; do
      if [[ "$file" -nt "$RUN_MARKER" ]]; then
        fresh_files+=("$file")
      fi
    done
  fi

  if [[ ${#fresh_files[@]} -eq 0 ]]; then
    error "No CSV files appear to have been created by the latest run."
    exit 1
  fi

  success "${#fresh_files[@]} fresh CSV file(s) verified."

  local latest_particle
  latest_particle="$(
    find "$OUTPUT_DIR" -maxdepth 1 -type f \
      -name 'particles_step_*.csv' \
      -printf '%f\n' 2>/dev/null |
    sort -V |
    tail -1
  )"

  if [[ -n "$latest_particle" ]]; then
    echo "       Latest particle snapshot: $latest_particle"
  fi
}

verify_website() {
  local required_files=(
    "$DASHBOARD_INDEX"
    "$DASHBOARD_STYLE"
    "$DASHBOARD_JS"
    "$DASHBOARD_MANIFEST"
  )

  local missing=()
  local file

  for file in "${required_files[@]}"; do
    [[ -s "$file" ]] || missing+=("$file")
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    error "Required website files are missing or empty:"
    for file in "${missing[@]}"; do
      echo "       $file" >&2
    done
    exit 1
  fi

  success "Generated website verified."

  local png_count=0
  local html_count=0
  local animation_count=0

  [[ -d "$VIZ_OUTPUT_DIR/png" ]] &&
    png_count="$(find "$VIZ_OUTPUT_DIR/png" -maxdepth 1 -type f | wc -l)"

  [[ -d "$VIZ_OUTPUT_DIR/html" ]] &&
    html_count="$(find "$VIZ_OUTPUT_DIR/html" -maxdepth 1 -type f | wc -l)"

  [[ -d "$VIZ_OUTPUT_DIR/animations" ]] &&
    animation_count="$(find "$VIZ_OUTPUT_DIR/animations" -maxdepth 1 -type f | wc -l)"

  echo "       PNG files:       $png_count"
  echo "       HTML viewers:    $html_count"
  echo "       Animation files: $animation_count"
}

# =============================================================================
# Pipeline
# =============================================================================

echo ""
echo -e "${BOLD}================================================================${RESET}"
echo -e "${BOLD}   AtmosphericSimulation — Safe Full Pipeline${RESET}"
echo -e "${BOLD}================================================================${RESET}"
echo ""
echo "  Project root:         $SCRIPT_DIR"
echo "  Build directory:      $BUILD_DIR"
echo "  Simulation output:    $OUTPUT_DIR"
echo "  Visualization output: $VIZ_OUTPUT_DIR"
echo "  Visualization only:   $VISUALIZATION_ONLY"
echo "  Max particles:        $MAX_PARTICLES"
echo ""

# ---- Pre-flight checks -------------------------------------------------------
[[ -f "$SCRIPT_DIR/CMakeLists.txt" ]] || {
  error "Missing CMakeLists.txt in $SCRIPT_DIR"
  exit 1
}

[[ -f "$VIZ_SCRIPT" ]] || {
  error "Missing visualization builder: $VIZ_SCRIPT"
  exit 1
}

command -v cmake >/dev/null 2>&1 || {
  error "cmake was not found in PATH."
  exit 1
}

PYTHON_EXECUTABLE="$(select_python)"

if ! command -v "$PYTHON_EXECUTABLE" >/dev/null 2>&1; then
  error "Python interpreter not found: $PYTHON_EXECUTABLE"
  exit 1
fi

info "Selected Python interpreter:"
echo "       $PYTHON_EXECUTABLE"

# Important: verify dependencies and dashboard files before deleting anything.
check_dependencies "$PYTHON_EXECUTABLE"
restore_dashboard_shell

# Warn about obsolete CSV files in the old root/output directory.
if [[ -d "$LEGACY_OUTPUT_DIR" ]]; then
  shopt -s nullglob
  legacy_csv_files=("$LEGACY_OUTPUT_DIR"/*.csv)
  shopt -u nullglob

  if [[ ${#legacy_csv_files[@]} -gt 0 ]]; then
    warn "Legacy CSV files exist in $LEGACY_OUTPUT_DIR"
    warn "They are ignored. This script reads only $OUTPUT_DIR"
  fi
fi

# ---- Build and simulation ----------------------------------------------------
if [[ "$VISUALIZATION_ONLY" == false ]]; then
  info "[1/6] Configuring C++ project..."

  cmake \
    -S "$SCRIPT_DIR" \
    -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

  success "CMake configuration complete."

  info "[2/6] Building C++ project..."

  NPROC="$(nproc 2>/dev/null || echo 4)"
  cmake --build "$BUILD_DIR" --parallel "$NPROC"

  success "Build complete."

  info "Locating simulation executable..."

  EXEC="$(
    find "$BUILD_DIR" -maxdepth 4 -type f -executable \
      \( -name AtmosphericSimulation -o -name atmospheric_simulation \) \
      -print -quit 2>/dev/null
  )"

  if [[ -z "$EXEC" ]]; then
    error "Could not find the simulation executable in $BUILD_DIR"
    exit 1
  fi

  success "Simulation executable found:"
  echo "       $EXEC"

  if [[ "$CLEAN_SIMULATION_OUTPUT" == true ]]; then
    clean_simulation_output
  else
    mkdir -p "$OUTPUT_DIR"
    warn "Existing simulation output is being preserved."
    warn "Old and new CSV files may be mixed."
  fi

  RUN_MARKER="$BUILD_DIR/.pipeline_run_started"
  touch "$RUN_MARKER"

  info "[3/6] Running simulation..."
  echo "       Working directory: $BUILD_DIR"

  (
    cd "$BUILD_DIR"
    "$EXEC"
  )

  success "Simulation finished."

  info "[4/6] Verifying fresh CSV output..."
  verify_fresh_csv
else
  info "[1–4/6] Visualization-only mode selected."
  info "Skipping CMake configuration, build, and simulation."
  verify_existing_csv
fi

# ---- Visualization -----------------------------------------------------------
if [[ "$CLEAN_GENERATED_VISUALIZATIONS" == true ]]; then
  clean_generated_visualizations
else
  warn "Existing generated visualization artifacts are being preserved."
fi

info "[5/6] Generating visualizations..."

VIZ_ARGS=(
  "$VIZ_SCRIPT"
  --input "$OUTPUT_DIR"
  --out "$VIZ_OUTPUT_DIR"
  --max-particles "$MAX_PARTICLES"
  --verbose
)

[[ "$SKIP_ANIMATION" == true ]] && VIZ_ARGS+=(--skip-animation)
[[ "$OPEN_DASHBOARD" == true ]] && VIZ_ARGS+=(--open-dashboard)

"$PYTHON_EXECUTABLE" "${VIZ_ARGS[@]}"

success "Visualization builder finished."

info "[6/6] Verifying generated website..."
verify_website

# ---- Final summary -----------------------------------------------------------
echo ""
echo -e "${BOLD}================================================================${RESET}"
echo -e "${GREEN}${BOLD}   Pipeline complete!${RESET}"
echo -e "${BOLD}================================================================${RESET}"
echo ""
echo "  Simulation data:"
echo "    $OUTPUT_DIR"
echo ""
echo "  Dashboard:"
echo "    $DASHBOARD_INDEX"
echo ""
echo "  Start the local web server:"
echo "    cd \"$VIZ_OUTPUT_DIR\""
echo "    \"$PYTHON_EXECUTABLE\" -m http.server 8000"
echo ""
echo "  Open:"
echo "    http://localhost:8000/"
echo ""

if grep -qi microsoft /proc/version 2>/dev/null; then
  echo "  WSL browser command:"
  echo "    explorer.exe http://localhost:8000/"
  echo ""
fi
