#include "analysis/StreamfunctionCalculator.h"
#include <cmath>
#include <algorithm>
#include <limits>

// ----------------------------------------------------------------
// Integration convention
// ----------------------------------------------------------------
// dh = atmosphereHeight / circulationAltitudeBins
//
// Psi[lat][0]   = massFlux[lat][0]   * dh           (surface layer)
// Psi[lat][alt] = Psi[lat][alt-1] + massFlux[lat][alt] * dh
//
// Empty bins (samples == 0):
//   massFlux is treated as 0.0 for that layer.
//   runningPsi is not advanced, so the integral carries forward the
//   last non-zero contribution — this avoids artificial discontinuities
//   in the Psi field when isolated bins are empty.
// ----------------------------------------------------------------

std::vector<StreamfunctionCell> StreamfunctionCalculator::compute(
    const std::vector<CirculationCellAverages>& averages,
    const SimulationConfig&                     config) const
{
    const int    nLat = config.circulationLatitudeBins;
    const int    nAlt = config.circulationAltitudeBins;
    const double dh   = config.atmosphereHeight / static_cast<double>(nAlt);

    // Flat 2-D lookup grids: index = latIdx * nAlt + altIdx
    std::vector<double> massFluxGrid(nLat * nAlt, 0.0);
    std::vector<double> vThetaGrid  (nLat * nAlt, 0.0);
    std::vector<int>    samplesGrid (nLat * nAlt, 0);

    // Fill grids from accumulator output.
    // Out-of-range or non-finite values are safely ignored.
    for (const auto& cell : averages) {
        if (cell.latIndex < 0 || cell.latIndex >= nLat) continue;
        if (cell.altIndex < 0 || cell.altIndex >= nAlt) continue;

        const int idx = cell.latIndex * nAlt + cell.altIndex;
        massFluxGrid[idx] = std::isfinite(cell.meanMassFlux) ? cell.meanMassFlux : 0.0;
        vThetaGrid[idx]   = std::isfinite(cell.meanVTheta)   ? cell.meanVTheta   : 0.0;
        samplesGrid[idx]  = cell.samples;
    }

    // Integrate mass flux upward for each latitude band.
    std::vector<double> psiGrid(nLat * nAlt, 0.0);

    for (int latIdx = 0; latIdx < nLat; ++latIdx) {
        double runningPsi = 0.0;
        for (int altIdx = 0; altIdx < nAlt; ++altIdx) {
            const int idx  = latIdx * nAlt + altIdx;
            runningPsi    += massFluxGrid[idx] * dh;  // += 0 for empty bins
            psiGrid[idx]   = runningPsi;
        }
    }

    // Build the complete rectangular output (all nLat x nAlt cells).
    std::vector<StreamfunctionCell> results;
    results.reserve(nLat * nAlt);

    for (int latIdx = 0; latIdx < nLat; ++latIdx) {
        const double latCenter = (latIdx + 0.5) / nLat * 180.0 - 90.0;

        for (int altIdx = 0; altIdx < nAlt; ++altIdx) {
            const int    idx       = latIdx * nAlt + altIdx;
            const double altCenter = (altIdx + 0.5) / nAlt * config.atmosphereHeight;

            StreamfunctionCell sc;
            sc.latitudeBin       = latIdx;
            sc.altitudeBin       = altIdx;
            sc.latitudeCenterDeg = latCenter;
            sc.altitudeCenter    = altCenter;
            sc.samples           = samplesGrid[idx];
            sc.meanVTheta        = vThetaGrid[idx];
            sc.meanMassFlux      = massFluxGrid[idx];
            sc.psi               = psiGrid[idx];
            results.push_back(sc);
        }
    }

    return results;
}

StreamfunctionSummary StreamfunctionCalculator::summarize(
    const std::vector<StreamfunctionCell>& cells) const
{
    StreamfunctionSummary summary;
    summary.minPsi = std::numeric_limits<double>::max();
    summary.maxPsi = std::numeric_limits<double>::lowest();

    for (const auto& sc : cells) {
        if (!std::isfinite(sc.psi)) continue;
        summary.maxAbsPsi = std::max(summary.maxAbsPsi, std::abs(sc.psi));
        summary.minPsi    = std::min(summary.minPsi,    sc.psi);
        summary.maxPsi    = std::max(summary.maxPsi,    sc.psi);
        if (sc.samples > 0) ++summary.cellsWithSamples;
    }

    // Guard: no valid cells at all
    if (summary.minPsi == std::numeric_limits<double>::max()) {
        summary.minPsi = 0.0;
        summary.maxPsi = 0.0;
    }

    return summary;
}
