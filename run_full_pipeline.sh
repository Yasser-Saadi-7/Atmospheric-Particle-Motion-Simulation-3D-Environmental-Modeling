#!/usr/bin/env bash
# =============================================================================
# run_full_pipeline.sh
# AtmosphericSimulation — full end-to-end pipeline
#
# Steps:
#   1. Build the C++ project with CMake
#   2. Run the simulation executable
#   3. Verify output/*.csv was created
#   4. Generate visualizations with Stage UI-3 builder
#   5. (Optional) Open the dashboard
#
# Usage:
#   bash run_full_pipeline.sh
#   bash run_full_pipeline.sh --skip-animation
#   bash run_full_pipeline.sh --open-dashboard
#
# This script does NOT modify any C++ source files, src/, CMakeLists.txt,
# or physics/simulation logic.
# =============================================================================

set -euo pipefail

# ---- Paths ----------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
OUTPUT_DIR="$SCRIPT_DIR/output"
VIZ_SCRIPT="$SCRIPT_DIR/visualization/build_dashboard.py"

# ---- CLI flags ---------------------------------------------------------------
SKIP_ANIM=""
OPEN_DASH=""
for arg in "$@"; do
  case "$arg" in
    --skip-animation) SKIP_ANIM="--skip-animation" ;;
    --open-dashboard) OPEN_DASH="--open-dashboard"  ;;
    --help|-h)
      echo "Usage: bash run_full_pipeline.sh [--skip-animation] [--open-dashboard]"
      exit 0
      ;;
  esac
done

# ---- Colours (ANSI) ----------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
err()     { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

# =============================================================================
echo ""
echo -e "${BOLD}================================================================${RESET}"
echo -e "${BOLD}   AtmosphericSimulation — Full Pipeline${RESET}"
echo -e "${BOLD}================================================================${RESET}"
echo ""

# ---- [1] Build ---------------------------------------------------------------
info "[1/4] Configuring and building C++ project..."
cmake -B "$BUILD_DIR" -S "$SCRIPT_DIR" -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXPORT_COMPILE_COMMANDS=ON 2>&1 | grep -E 'error:|warning:|Configuring|Building|--' || true

NPROC=$(nproc 2>/dev/null || echo 4)
cmake --build "$BUILD_DIR" --parallel "$NPROC"
success "Build complete."

# ---- [2] Run simulation -------------------------------------------------------
info "[2/4] Finding and running simulation executable..."

EXEC=$(find "$BUILD_DIR" -maxdepth 3 \
       \( -name "AtmosphericSimulation" -o -name "atmospheric_simulation" \) \
       -type f -executable 2>/dev/null | head -1)

if [[ -z "$EXEC" ]]; then
  err "Could not find simulation executable in $BUILD_DIR"
  err "Expected: AtmosphericSimulation (or atmospheric_simulation)"
  exit 1
fi

info "  Executable: $EXEC"
"$EXEC"
success "Simulation finished."

# ---- [3] Verify outputs -------------------------------------------------------
info "[3/4] Verifying CSV outputs..."
shopt -s nullglob
csv_files=("$OUTPUT_DIR"/*.csv)
shopt -u nullglob

if [[ ${#csv_files[@]} -eq 0 ]]; then
  warn "No CSV files found in $OUTPUT_DIR"
  warn "The dashboard will show missing data for all data-dependent plots."
else
  success "${#csv_files[@]} CSV file(s) found in output/:"
  for f in "${csv_files[@]}"; do
    echo "       $(basename "$f")"
  done
fi

# ---- [4] Generate visualizations ---------------------------------------------
info "[4/4] Generating visualizations with Stage UI-3 builder..."

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null; then
  err "python3 not found.  Install Python 3 and the required packages:"
  err "  pip install pandas numpy matplotlib plotly imageio"
  exit 1
fi

"$PYTHON" "$VIZ_SCRIPT" \
  --input  "$OUTPUT_DIR" \
  --out    "$SCRIPT_DIR/visualization_output" \
  --max-particles 5000 \
  $SKIP_ANIM \
  $OPEN_DASH \
  --verbose

# ---- Done --------------------------------------------------------------------
echo ""
echo -e "${BOLD}================================================================${RESET}"
echo -e "${GREEN}${BOLD}   Pipeline complete!${RESET}"
echo -e "${BOLD}================================================================${RESET}"
echo ""
echo "  Open the dashboard:"
echo "    visualization_output/index.html"
if grep -qi microsoft /proc/version 2>/dev/null; then
  # Running inside WSL
  WIN_PATH=$(wslpath -w "$SCRIPT_DIR/visualization_output/index.html" 2>/dev/null || true)
  if [[ -n "$WIN_PATH" ]]; then
    echo "    WSL: explorer.exe \"$WIN_PATH\""
  fi
fi
echo ""
