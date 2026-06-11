#include "analysis/CirculationAccumulator.h"
#include "utils/SphericalUtils.h"
#include <cmath>
#include <algorithm>
#include <iostream>

// Bin-index formulas (verified against edge cases):
//
//   Latitude  : latIdx = floor((latDeg + 90) / 180 * nLat)
//     lat=-90 -> 0/180*36=0          (bin 0)
//     lat=  0 -> 90/180*36=18        (bin 18)
//     lat=+90 -> 180/180*36=36  clamp-> 35
//   Center of bin i: (i+0.5)/nLat*180 - 90
//
//   Altitude  : altIdx = floor(alt / H * nAlt)
//     alt=0   -> 0                   (bin 0)
//     alt=H   -> H/H*20=20     clamp-> 19
//   Center of bin j: (j+0.5)/nAlt * H

CirculationAccumulator::CirculationAccumulator()
    : latBins_(0), altBins_(0), totalAccumulationCalls_(0) {}

void CirculationAccumulator::configure(const SimulationConfig& config) {
    latBins_ = config.circulationLatitudeBins;
    altBins_ = config.circulationAltitudeBins;
    bins_.assign(latBins_ * altBins_, CirculationBin{});
    totalAccumulationCalls_ = 0;
}

void CirculationAccumulator::reset() {
    std::fill(bins_.begin(), bins_.end(), CirculationBin{});
    totalAccumulationCalls_ = 0;
}

void CirculationAccumulator::accumulate(
    const std::vector<Parcel>& particles,
    const SimulationConfig&    config,
    int                        /*step*/)
{
    if (latBins_ == 0 || altBins_ == 0) {
        std::cerr << "[CirculationAccumulator] ERROR: configure() must be called before accumulate().\n";
        return;
    }

    const int totalBins = latBins_ * altBins_;

    // Temporary per-step arrays — reset each call
    std::vector<int>    stepCount(totalBins, 0);
    std::vector<double> stepVThetaSum(totalBins, 0.0);

    // --- Pass 1: bin every particle ---
    for (const auto& p : particles) {
        SphericalState s = computeSphericalState(
            p.r, p.v, config.planetRadius, config.angularVelocity);

        // Skip particles with invalid spherical state
        if (!std::isfinite(s.latitudeDeg)        ||
            !std::isfinite(s.altitude)            ||
            !std::isfinite(s.meridionalVelocity)) continue;

        // Skip particles outside the atmospheric shell
        if (s.altitude < 0.0 || s.altitude > config.atmosphereHeight) continue;

        // Map to bin indices
        int latIdx = static_cast<int>((s.latitudeDeg + 90.0) / 180.0 * latBins_);
        int altIdx = static_cast<int>(s.altitude / config.atmosphereHeight * altBins_);

        latIdx = std::clamp(latIdx, 0, latBins_ - 1);
        altIdx = std::clamp(altIdx, 0, altBins_ - 1);

        const int binIdx = latIdx * altBins_ + altIdx;
        ++stepCount[binIdx];
        stepVThetaSum[binIdx] += s.meridionalVelocity;
    }

    // --- Pass 2: merge this snapshot into the running accumulators ---
    // For each occupied bin, compute per-step means and add to long-run sums.
    // densityProxy = particle count in bin (simple first-order approximation of rho).
    // massFlux = densityProxy * meanVTheta  (proxy for rho * v_theta).
    for (int latIdx = 0; latIdx < latBins_; ++latIdx) {
        for (int altIdx = 0; altIdx < altBins_; ++altIdx) {
            const int binIdx = latIdx * altBins_ + altIdx;
            const int n      = stepCount[binIdx];
            if (n == 0) continue;

            const double meanVTheta   = stepVThetaSum[binIdx] / n;
            const double densityProxy = static_cast<double>(n);
            const double massFlux     = densityProxy * meanVTheta;

            CirculationBin& bin = bins_[binIdx];
            bin.particleCountSum   += n;
            bin.densityProxySum    += densityProxy;
            bin.vThetaSum          += meanVTheta;
            bin.vThetaSquaredSum   += meanVTheta * meanVTheta;
            bin.massFluxSum        += massFlux;
            ++bin.samples;
        }
    }

    ++totalAccumulationCalls_;
}

std::vector<CirculationCellAverages> CirculationAccumulator::computeAverages(
    const SimulationConfig& config) const
{
    std::vector<CirculationCellAverages> results;
    results.reserve(latBins_ * altBins_);

    for (int latIdx = 0; latIdx < latBins_; ++latIdx) {
        const double latCenter = (latIdx + 0.5) / latBins_ * 180.0 - 90.0;

        for (int altIdx = 0; altIdx < altBins_; ++altIdx) {
            const CirculationBin& bin = bins_[latIdx * altBins_ + altIdx];
            if (bin.samples == 0) continue;

            const double altCenter = (altIdx + 0.5) / altBins_ * config.atmosphereHeight;
            const double s         = static_cast<double>(bin.samples);

            CirculationCellAverages cell;
            cell.latIndex          = latIdx;
            cell.altIndex          = altIdx;
            cell.latitudeCenterDeg = latCenter;
            cell.altitudeCenter    = altCenter;
            cell.samples           = bin.samples;
            cell.meanParticleCount = bin.particleCountSum / s;
            cell.meanDensityProxy  = bin.densityProxySum  / s;
            cell.meanVTheta        = bin.vThetaSum        / s;

            // Variance: E[x²] - E[x]²  (clamped to avoid sqrt of tiny negatives)
            const double variance = bin.vThetaSquaredSum / s
                                    - cell.meanVTheta * cell.meanVTheta;
            cell.stdVTheta        = (variance > 0.0) ? std::sqrt(variance) : 0.0;

            cell.meanMassFlux = bin.massFluxSum / s;
            results.push_back(cell);
        }
    }

    return results;
}

bool CirculationAccumulator::hasSamples() const {
    for (const auto& bin : bins_) {
        if (bin.samples > 0) return true;
    }
    return false;
}

int CirculationAccumulator::getTotalAccumulationCalls() const {
    return totalAccumulationCalls_;
}
