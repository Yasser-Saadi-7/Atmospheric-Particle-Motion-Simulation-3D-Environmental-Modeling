#pragma once

#include <vector>
#include "analysis/CirculationAccumulator.h"
#include "model/SimulationConfig.h"

// ============================================================
// Per-cell result of the streamfunction computation.
// One entry per (latitude, altitude) bin — including empty bins
// so the output grid is always rectangular and complete.
// ============================================================
struct StreamfunctionCell {
    int    latitudeBin;        // latitude bin index  [0, nLatBins)
    int    altitudeBin;        // altitude bin index  [0, nAltBins)
    double latitudeCenterDeg;  // bin centre latitude in degrees  [-90, 90]
    double altitudeCenter;     // bin centre altitude in model units  [0, H]
    int    samples;            // accumulation count (0 = empty bin)
    double meanVTheta;         // time-averaged northward meridional velocity
    double meanMassFlux;       // time-averaged density-proxy * v_theta  (proxy for rho*v_theta)
    double psi;                // streamfunction Psi at this cell [model units]
};

// ============================================================
// Summary statistics for one streamfunction output step.
// ============================================================
struct StreamfunctionSummary {
    double maxAbsPsi        = 0.0;
    double minPsi           = 0.0;
    double maxPsi           = 0.0;
    int    cellsWithSamples = 0;
};

// ============================================================
// StreamfunctionCalculator
//
// Computes the meridional overturning streamfunction Psi(lat, alt)
// from the time-averaged meridional mass flux produced by
// CirculationAccumulator.
//
// Physical background:
//   - Psi is computed by vertically integrating the longitude-averaged
//     meridional mass flux from the surface (alt = 0) upward:
//
//       Psi[lat][0]   = massFlux[lat][0]   * dh
//       Psi[lat][alt] = Psi[lat][alt-1] + massFlux[lat][alt] * dh
//
//   - mean_mass_flux is an approximation to rho * v_theta in model units.
//   - Positive and negative Psi values indicate opposite circulation
//     directions (clockwise vs. counter-clockwise cells).
//   - Time averaging by CirculationAccumulator is essential; instantaneous
//     particle snapshots are too noisy to reveal stable circulation cells.
//   - This class only computes Psi. Visualization and cell identification
//     (Hadley / Ferrel / Polar) are handled separately.
//   - Empty bins contribute zero to the running integral (carry-forward
//     convention) to avoid discontinuities in the Psi field.
// ============================================================
class StreamfunctionCalculator {
public:
    // Build the complete Psi grid from CirculationAccumulator output.
    // All nLat × nAlt bins are returned — empty bins get psi from carry-forward.
    std::vector<StreamfunctionCell> compute(
        const std::vector<CirculationCellAverages>& averages,
        const SimulationConfig&                     config
    ) const;

    // Compute summary statistics over all cells (finite values only).
    StreamfunctionSummary summarize(
        const std::vector<StreamfunctionCell>& cells
    ) const;
};
