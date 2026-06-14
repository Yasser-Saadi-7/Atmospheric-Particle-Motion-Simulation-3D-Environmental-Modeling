#pragma once

#include <vector>
#include <string>
#include <unordered_map>
#include "model/Parcel.h"
#include "analysis/Diagnostics.h"
#include "analysis/CirculationAccumulator.h"
#include "analysis/StreamfunctionCalculator.h"
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

    // ----------------------------------------------------
    // Stage 4 Sprint 4.5 Outputs
    // ----------------------------------------------------
    // Appends one row to output/condensation_log.csv.
    // "ThisStep" values should be reset by the caller after each write.
    void appendCondensationLog(int step,
        double condensationThisStep, double cumulativeCondensation,
        double latentHeatingThisStep, double cumulativeLatentHeating,
        long long eventsThisStep, long long cumulativeEvents);

    // ----------------------------------------------------
    // Stage 4 Sprint 4.6 Outputs
    // ----------------------------------------------------
    // Appends one row to output/evaporation_log.csv.
    // "ThisStep" values should be reset by the caller after each write.
    void appendEvaporationLog(int step,
        double evaporationThisStep, double cumulativeEvaporation,
        long long eventsThisStep, long long cumulativeEvents);

    // ----------------------------------------------------
    // Stage 4 Sprint 4.7 Outputs
    // ----------------------------------------------------
    // Appends one row to output/moisture_balance.csv with full water balance accounting.
    void appendMoistureBalanceLog(int step,
        double totalQ, double initialTotalQ,
        double cumulativeEvaporation, double cumulativeCondensation,
        double expectedTotalQ, double waterBalanceError,
        double waterBalanceRelativeError, const std::string& status);

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

    // Writes the streamfunction Psi grid to output/streamfunction_step_XXXXX.csv
    // and appends one summary row to output/streamfunction_summary.csv.
    void writeStreamfunction(
        int step,
        const std::vector<StreamfunctionCell>&  cells,
        const StreamfunctionSummary&            summary);

private:
    std::string outputDir;
    bool logHeaderWritten;
    bool zoneHeaderWritten;
    bool sphericalFirstWritten;              // triggers one-time summary on first Stage 3 write
    bool streamfunctionSummaryHeaderWritten; // written once to streamfunction_summary.csv
    bool condensationLogHeaderWritten;       // written once to condensation_log.csv
    bool evaporationLogHeaderWritten;        // written once to evaporation_log.csv
    bool moistureBalanceLogHeaderWritten;    // written once to moisture_balance.csv

    std::string formatStepZeroPadded(int step, int width = 5) const;
};