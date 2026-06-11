#include "analysis/Diagnostics.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>

namespace Diagnostics {

    // ... [Stage 1 Implementations remain completely unchanged] ...
    std::vector<RadialDensityBin> computeRadialDensityProfile(const std::vector<Parcel>& parcels, const SimulationConfig& config, int numBins) {
        std::vector<RadialDensityBin> profile(numBins);
        double R_inner = config.planetRadius;
        double R_outer = config.planetRadius + config.atmosphereHeight;
        double binWidth = (R_outer - R_inner) / numBins;

        for (int i = 0; i < numBins; ++i) {
            double r_start = R_inner + i * binWidth;
            double r_end = r_start + binWidth;
            profile[i].rCenter = r_start + 0.5 * binWidth;
            profile[i].count = 0;
            double vol = (4.0 / 3.0) * M_PI * (std::pow(r_end, 3) - std::pow(r_start, 3));
            profile[i].numberDensity = vol; 
        }

        for (const auto& p : parcels) {
            double r = p.r.norm();
            if (r >= R_inner && r <= R_outer) {
                int binIdx = static_cast<int>((r - R_inner) / binWidth);
                if (binIdx >= 0 && binIdx < numBins) profile[binIdx].count++;
            }
        }

        for (int i = 0; i < numBins; ++i) {
            if (profile[i].numberDensity > 0.0) profile[i].numberDensity = profile[i].count / profile[i].numberDensity;
        }
        return profile;
    }

    DensityValidationResult validateDensityProfile(const std::vector<RadialDensityBin>& profile, double tolerance) {
        DensityValidationResult res = {true, 0.0};
        for (size_t i = 1; i < profile.size(); ++i) {
            double prevDensity = profile[i-1].numberDensity;
            double currDensity = profile[i].numberDensity;
            if (prevDensity > 0.0) {
                double increase = (currDensity - prevDensity) / prevDensity;
                if (increase > res.maxFluctuation) res.maxFluctuation = increase;
                if (increase > tolerance) res.isApproximatelyMonotonic = false;
            }
        }
        return res;
    }

    ShellBoundsCheck checkShellBounds(const std::vector<Parcel>& parcels, const SimulationConfig& config) {
        ShellBoundsCheck result = {true, 0, std::numeric_limits<double>::max(), 0.0};
        double R_inner = config.planetRadius;
        double R_outer = config.planetRadius + config.atmosphereHeight;
        double epsilon = 1e-7;

        for (const auto& p : parcels) {
            double r = p.r.norm();
            if (r < result.minRadius) result.minRadius = r;
            if (r > result.maxRadius) result.maxRadius = r;
            if (r < R_inner - epsilon || r > R_outer + epsilon) result.outsideCount++;
        }
        result.allInside = (result.outsideCount == 0);
        return result;
    }

    EnergyReport computeEnergyReport(const std::vector<Parcel>& parcels, const FineGrid& fineGrid, const SimulationConfig& config) {
        EnergyReport report = {0.0, 0.0, 0.0, 0.0};
        for (const auto& p : parcels) {
            report.kinetic += 0.5 * p.mass * p.v.squaredNorm();
            report.gravitational += p.mass * config.gravity * p.r.norm();
        }
        double sigma_sq = config.sigma * config.sigma;
        for (size_t i = 0; i < parcels.size(); ++i) {
            const Parcel& p_i = parcels[i];
            CellIndex cell = fineGrid.positionToCell(p_i.r);
            std::array<CellIndex, 27> neighbors = fineGrid.getNeighborCells(cell);
            for (const auto& neighborCell : neighbors) {
                for (int j_idx : fineGrid.getCellParticles(neighborCell)) {
                    if (j_idx > static_cast<int>(i)) {
                        const Parcel& p_j = parcels[j_idx];
                        double r_sq = (p_i.r - p_j.r).squaredNorm();
                        if (r_sq > 0.0 && r_sq < sigma_sq) {
                            double diff = sigma_sq - r_sq;
                            report.repulsion += 0.5 * config.repulsionStiffness * diff * diff;
                        }
                    }
                }
            }
        }
        report.total = report.kinetic + report.gravitational + report.repulsion;
        return report;
    }

    void saveRadialDensityProfile(const std::vector<RadialDensityBin>& profile, const std::string& filepath) {
        std::ofstream file(filepath);
        if (!file.is_open()) return;
        file << "r_center,count,number_density\n";
        for (const auto& bin : profile) file << bin.rCenter << "," << bin.count << "," << bin.numberDensity << "\n";
        file.close();
    }

    // ----------------------------------------------------
    // Stage 2 Implementations
    // ----------------------------------------------------

    Stage2ValidationReport computeStage2ValidationReport(const CoarseGrid& coarseGrid, const SimulationConfig& config, int numAltitudeBins) {
        Stage2ValidationReport report;
        
        // Initialize structures
        report.zoneTemperatures = {0.0, 0.0, 0.0, 0, 0, 0};
        report.equatorialRadialVelocity = {0.0, 0};
        
        report.altitudeTemperatureProfile.resize(numAltitudeBins);
        double binWidth = config.atmosphereHeight / numAltitudeBins;
        for (int i = 0; i < numAltitudeBins; ++i) {
            report.altitudeTemperatureProfile[i].altitudeCenter = (i + 0.5) * binWidth;
            report.altitudeTemperatureProfile[i].meanTemperature = 0.0;
            report.altitudeTemperatureProfile[i].count = 0;
        }

        const double LAT_30 = M_PI / 6.0;
        const double LAT_60 = M_PI / 3.0;

        double sumEqT = 0.0, sumMidT = 0.0, sumPolarT = 0.0;
        double sumEqVr = 0.0;

        // Iterate over macroscopic cells to accumulate weighted averages
        for (const auto& pair : coarseGrid.getAllOccupiedCells()) {
            const CoarseCellData& cell = pair.second;
            if (cell.particleCount == 0) continue;

            double absLat = std::abs(cell.latitude);
            double t_kin = cell.meanKineticTemperature;
            int count = cell.particleCount;

            // 1. Latitude Zones (Temperature)
            if (absLat < LAT_30) {
                sumEqT += t_kin * count;
                report.zoneTemperatures.equatorialCount += count;
                
                // Radial Velocity for Equatorial Band
                if (cell.cellRadius > 1e-9) {
                    double v_r = cell.meanVelocity.dot(cell.cellCenter) / cell.cellRadius;
                    sumEqVr += v_r * count;
                    report.equatorialRadialVelocity.sampleCount += count;
                }
            } else if (absLat < LAT_60) {
                sumMidT += t_kin * count;
                report.zoneTemperatures.midLatitudeCount += count;
            } else {
                sumPolarT += t_kin * count;
                report.zoneTemperatures.polarCount += count;
            }

            // 2. Altitude Bins
            int binIdx = static_cast<int>(cell.altitude / binWidth);
            if (binIdx >= 0 && binIdx < numAltitudeBins) {
                report.altitudeTemperatureProfile[binIdx].meanTemperature += t_kin * count;
                report.altitudeTemperatureProfile[binIdx].count += count;
            }
        }

        // Finalize Temperature Averages
        if (report.zoneTemperatures.equatorialCount > 0) report.zoneTemperatures.equatorialMean = sumEqT / report.zoneTemperatures.equatorialCount;
        if (report.zoneTemperatures.midLatitudeCount > 0) report.zoneTemperatures.midLatitudeMean = sumMidT / report.zoneTemperatures.midLatitudeCount;
        if (report.zoneTemperatures.polarCount > 0) report.zoneTemperatures.polarMean = sumPolarT / report.zoneTemperatures.polarCount;

        // Finalize Radial Velocity Average
        if (report.equatorialRadialVelocity.sampleCount > 0) {
            report.equatorialRadialVelocity.meanRadialVelocity = sumEqVr / report.equatorialRadialVelocity.sampleCount;
        }

        // Finalize Altitude Profile Averages
        for (auto& bin : report.altitudeTemperatureProfile) {
            if (bin.count > 0) {
                bin.meanTemperature /= bin.count;
            }
        }

        // Validate Key Stage 2 Criteria
        report.equatorWarmerThanPolar = (report.zoneTemperatures.equatorialMean > report.zoneTemperatures.polarMean);
        report.positiveEquatorialUpwelling = (report.equatorialRadialVelocity.meanRadialVelocity > 0.0);

        return report;
    }

    void saveAltitudeTemperatureProfile(const std::vector<AltitudeTemperatureBin>& profile, const std::string& filepath) {
        std::ofstream file(filepath);
        if (!file.is_open()) return;
        file << "altitude_center,count,mean_temperature\n";
        for (const auto& bin : profile) {
            file << bin.altitudeCenter << "," << bin.count << "," << bin.meanTemperature << "\n";
        }
        file.close();
    }

} // namespace Diagnostics