#pragma once

#include <vector>
#include <string>
#include "model/Parcel.h"
#include "model/SimulationConfig.h"
#include "simulation/FineGrid.h"
#include "simulation/CoarseGrid.h"

namespace Diagnostics {

    // ----------------------------------------------------
    // Stage 1 Diagnostics
    // ----------------------------------------------------
    struct RadialDensityBin {
        double rCenter;
        int count;
        double numberDensity; 
    };

    struct ShellBoundsCheck {
        bool allInside;
        int outsideCount;
        double minRadius;
        double maxRadius;
    };

    struct EnergyReport {
        double kinetic;
        double gravitational;
        double repulsion;
        double total;
    };

    struct DensityValidationResult {
        bool isApproximatelyMonotonic;
        double maxFluctuation;
    };

    std::vector<RadialDensityBin> computeRadialDensityProfile(const std::vector<Parcel>& parcels, const SimulationConfig& config, int numBins = 50);
    ShellBoundsCheck checkShellBounds(const std::vector<Parcel>& parcels, const SimulationConfig& config);
    DensityValidationResult validateDensityProfile(const std::vector<RadialDensityBin>& profile, double tolerance = 0.20);
    EnergyReport computeEnergyReport(const std::vector<Parcel>& parcels, const FineGrid& fineGrid, const SimulationConfig& config);
    void saveRadialDensityProfile(const std::vector<RadialDensityBin>& profile, const std::string& filepath);

    // ----------------------------------------------------
    // Stage 2 Diagnostics
    // ----------------------------------------------------
    struct LatitudeZoneTemperatureReport {
        double equatorialMean;  // 0 to 30 degrees
        double midLatitudeMean; // 30 to 60 degrees
        double polarMean;       // 60 to 90 degrees
        int equatorialCount;
        int midLatitudeCount;
        int polarCount;
    };

    struct AltitudeTemperatureBin {
        double altitudeCenter;
        double meanTemperature;
        int count;
    };

    struct RadialVelocityBandReport {
        double meanRadialVelocity;
        int sampleCount;
    };

    struct Stage2ValidationReport {
        LatitudeZoneTemperatureReport zoneTemperatures;
        std::vector<AltitudeTemperatureBin> altitudeTemperatureProfile;
        RadialVelocityBandReport equatorialRadialVelocity;
        
        bool equatorWarmerThanPolar;
        bool positiveEquatorialUpwelling;
    };

    // Computes all Stage 2 diagnostics in a single pass over the coarse grid
    Stage2ValidationReport computeStage2ValidationReport(const CoarseGrid& coarseGrid, const SimulationConfig& config, int numAltitudeBins = 20);

    // Helper to export the altitude-temperature profile
    void saveAltitudeTemperatureProfile(const std::vector<AltitudeTemperatureBin>& profile, const std::string& filepath);

} // namespace Diagnostics