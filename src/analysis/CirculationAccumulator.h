#pragma once

#include <vector>
#include "model/Parcel.h"
#include "model/SimulationConfig.h"

// ============================================================
// Raw per-bin accumulation state.
// One entry per (latitude, altitude) cell.
// Updated every circulationAccumulationInterval steps.
// ============================================================
struct CirculationBin {
    int    samples          = 0;    // number of steps that contributed to this bin
    double particleCountSum = 0.0;  // sum of particle counts across samples
    double densityProxySum  = 0.0;  // sum of density proxies (= particleCountSum here)
    double vThetaSum        = 0.0;  // sum of per-step mean meridional velocity
    double vThetaSquaredSum = 0.0;  // sum of squares for std computation
    double massFluxSum      = 0.0;  // sum of densityProxy * meanVTheta per step
};

// ============================================================
// Time-averaged output for one latitude-altitude cell.
// Returned by CirculationAccumulator::computeAverages().
// ============================================================
struct CirculationCellAverages {
    int    latIndex;            // latitude bin index [0, nLatBins)
    int    altIndex;            // altitude bin index [0, nAltBins)
    double latitudeCenterDeg;   // bin centre latitude in degrees
    double altitudeCenter;      // bin centre altitude in model units
    int    samples;             // number of accumulation calls with particles here
    double meanParticleCount;   // time-averaged particle count in this bin
    double meanDensityProxy;    // time-averaged density proxy (= meanParticleCount)
    double meanVTheta;          // time-averaged northward meridional velocity
    double stdVTheta;           // standard deviation of meanVTheta across samples
    double meanMassFlux;        // time-averaged proxy for rho * v_theta
};

// ============================================================
// CirculationAccumulator
//
// Accumulates longitude-averaged meridional circulation diagnostics
// in latitude-altitude bins, preparing data for the streamfunction
// Psi calculation in Sprint 4.
//
// Physical background:
//   - v_theta is the meridional (northward) velocity component from
//     SphericalUtils.
//   - meanMassFlux approximates rho * v_theta, the meridional mass flux
//     needed to compute the streamfunction Psi.
//   - Psi is NOT computed here; it will be integrated from the accumulated
//     mass flux in Sprint 4.
//   - Time averaging over many steps is essential: a single noisy snapshot
//     cannot reliably identify Hadley, Ferrel, or Polar circulation cells.
// ============================================================
class CirculationAccumulator {
public:
    CirculationAccumulator();

    // Must be called once before the first accumulate() call.
    void configure(const SimulationConfig& config);

    // Zero all accumulated data, keeping grid dimensions intact.
    void reset();

    // Add one snapshot of particle data to the running accumulation.
    // Safe to call repeatedly; each call adds one time sample per bin.
    void accumulate(
        const std::vector<Parcel>& particles,
        const SimulationConfig&    config,
        int                        step
    );

    // Compute time-averaged statistics over all accumulated snapshots.
    // Returns only cells with at least one sample.
    std::vector<CirculationCellAverages> computeAverages(
        const SimulationConfig& config
    ) const;

    // True if any bin has received at least one sample.
    bool hasSamples() const;

    int getTotalAccumulationCalls() const;

private:
    int latBins_;
    int altBins_;

    // Flat 2-D layout: bins_[latIndex * altBins_ + altIndex]
    std::vector<CirculationBin> bins_;

    int totalAccumulationCalls_;
};
