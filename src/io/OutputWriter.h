#pragma once

#include <vector>
#include <string>
#include <unordered_map>
#include "model/Parcel.h"
#include "analysis/Diagnostics.h"
#include "analysis/CirculationAccumulator.h"
#include "simulation/CoarseGrid.h" // Needed for CoarseCellData

class OutputWriter {
public:
    OutputWriter(const std::string& outputDir = "output");

    // ----------------------------------------------------
    // Stage 1 Outputs
    // ----------------------------------------------------
    void writeParticleSnapshot(const std::vector<Parcel>& parcels, int step) const;

    void appendSimulationLog(const std::vector<Parcel>& parcels, int step, 
                             const Diagnostics::EnergyReport& energy, 
                             const Diagnostics::ShellBoundsCheck& bounds);

    // ----------------------------------------------------
    // Stage 2 Outputs
    // ----------------------------------------------------
    // Logs the mean kinetic temperature for 3 distinct latitude bands
    void appendTemperatureZoneLog(int step, double tempEq, double tempMid, double tempPolar);

    // Dumps the full macroscopic state of all occupied coarse cells for heatmaps
    void writeCoarseGridSnapshot(const std::unordered_map<CoarseCellIndex, CoarseCellData, CoarseCellIndexHash>& cells, int step) const;

    // ----------------------------------------------------
    // Stage 3 Outputs
    // ----------------------------------------------------
    // Writes per-particle spherical-coordinate diagnostics to
    // output/particle_spherical_step_XXXXX.csv.
    // Called once at N2 (after rotation activation) and then every
    // sphericalDiagnosticsInterval steps.
    void writeParticleSphericalDiagnostics(
        const std::vector<Parcel>& parcels,
        int step,
        double planetRadius,
        double angularVelocity);

    // Writes time-averaged latitude-altitude circulation diagnostics to
    // output/circulation_accum_step_XXXXX.csv.
    // Only bins with samples > 0 are written.
    void writeCirculationAverages(
        int step,
        const std::vector<CirculationCellAverages>& averages);

private:
    std::string outputDir;
    bool logHeaderWritten;
    bool zoneHeaderWritten;
    bool sphericalFirstWritten;  // triggers one-time summary on first Stage 3 write

    std::string formatStepZeroPadded(int step, int width = 5) const;
};