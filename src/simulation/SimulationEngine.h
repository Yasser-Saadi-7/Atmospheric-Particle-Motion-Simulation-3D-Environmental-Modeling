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
};