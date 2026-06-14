#pragma once

#include <vector>
#include <random>
#include "model/Parcel.h"
#include "model/SimulationConfig.h"
#include "simulation/Environment.h"
#include "simulation/ThermalModel.h"
#include "simulation/FineGrid.h"
#include "simulation/CoarseGrid.h"
#include "simulation/Integrator.h"
#include "io/OutputWriter.h"
#include "analysis/CirculationAccumulator.h"
#include "analysis/StreamfunctionCalculator.h"

class SimulationEngine {
public:
    SimulationEngine(const SimulationConfig& config);

    void initializeParticles();
    
    // Normal run loop executing all active phases
    void run();

    // Specific validation routine to lock Stage 1 requirements
    void validateStage1();

private:
    void runPhase1();

    // Stage 2: Thermal Equilibration (Damping OFF, Thermal Collisions ON)
    void runPhase2();

    // Stage 3: Rotation and Circulation (one-time rotational velocity imprint at N2)
    void runPhase3();

    // Applies the planetary rotational velocity to every particle exactly once.
    // Rotation is about the z-axis: v += Omega x r => vx -= Omega*y, vy += Omega*x.
    // No explicit Coriolis force is added; deflection emerges from inertial dynamics.
    void activateRotation();

    // Executes the stochastic thermal collision process on all particles
    void applyThermalCollisions();

    // Stage 4 Sprint 4.5: condensation + latent heat release for all particles
    void applyCondensation();

    // Stage 4 Sprint 4.6: near-surface evaporation for particles in the lower layer
    void applyNearSurfaceEvaporation();

    // Stage 4 Sprint 4.7: water balance accounting
    double computeTotalSpecificHumidity() const;
    void   updateWaterBalanceDiagnostics(int step);

    // Grid management
    void updateCoarseGrid();

    // NEW: Helper to bin coarse grid cells into latitude zones and log them
    void logStage2Diagnostics();

    // Helper methods for initialization
    Vec3 sampleRandomPositionInShell();
    Vec3 sampleInitialVelocity(double temperature, double mass);
    void removeCenterOfMassDrift();

    // Core state
    SimulationConfig config;
    std::vector<Parcel> parcels;
    int currentStep;

    // Stage 3: set to true after activateRotation() runs to prevent re-application
    bool rotationActivated = false;
    // Stage 3: set to true when the circulation-accumulation start message is printed
    bool circulationLogPrinted = false;
    // Stage 3: set to true when the streamfunction start message is printed
    bool streamfunctionLogPrinted = false;

    // Stage 4 Sprint 4.5: condensation accumulators.
    // "ThisStep" counters are reset after each condensation log write (every logInterval).
    // "Cumulative" counters are never reset.
    double      condensationThisStep        = 0.0;
    double      cumulativeCondensation      = 0.0;
    double      latentHeatingThisStep       = 0.0;
    double      cumulativeLatentHeating     = 0.0;
    long long   condensationEventsThisStep  = 0;
    long long   cumulativeCondensationEvents = 0;

    // Stage 4 Sprint 4.6: evaporation accumulators (reset at log write, cumulative never reset).
    double      evaporationThisStep         = 0.0;
    double      cumulativeEvaporation       = 0.0;
    long long   evaporationEventsThisStep   = 0;
    long long   cumulativeEvaporationEvents = 0;

    // Stage 4 Sprint 4.7: water balance state (never reset after initialization).
    double initialTotalSpecificHumidity   = 0.0;
    double currentTotalSpecificHumidity   = 0.0;
    double waterBalanceExpected           = 0.0;
    double waterBalanceError              = 0.0;
    double waterBalanceRelativeError      = 0.0;
    bool   waterBalanceInitialized        = false;

    // Random number generation
    std::mt19937 rng;

    // Sub-systems
    Environment environment;
    ThermalModel thermalModel;
    FineGrid fineGrid;
    CoarseGrid coarseGrid;
    Integrator integrator;
    OutputWriter outputWriter;

    // Stage 3: longitude-averaged meridional circulation accumulator
    CirculationAccumulator circulationAccumulator;

    // Stage 3: computes Psi from accumulated mass flux
    StreamfunctionCalculator streamfunctionCalculator;
};