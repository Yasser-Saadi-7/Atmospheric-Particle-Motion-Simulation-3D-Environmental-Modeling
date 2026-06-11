#pragma once

struct SimulationConfig {
    // ====================================================
    // Stage 1: Core Simulation Parameters
    // ====================================================
    int numParticles = 10000;
    double dt = 0.01;

    // Geometry
    double planetRadius = 50.0;
    double atmosphereHeight = 20.0;

    // Physics & Forces
    double gravity = 0.016;
    double sigma = 2.0;
    double cutoffRadius = 2.0;
    double repulsionStiffness = 200.0;
    double maxForce = 100.0;
    
    // Damping & Boundaries
    double dampingGamma = 100.0;     // Friction applied during Phase 1 for equilibration
    double elasticityInner = 1.0;    // Rebound factor at r = R
    double elasticityOuter = 1.0;    // Rebound factor at r = R + H

    // ====================================================
    // Stage 1: Initialization & IO Parameters
    // ====================================================
    double initialTemperatureFactor = 0.1; // Temp factor for initial velocity distribution
    int logInterval = 1000;                // Output summary statistics interval
    int snapshotInterval = 5000;           // Output full particle state interval

    // ====================================================
    // Stage 2: Phase Control
    // ====================================================
    int phase1EndStep = 20000;       // N1: End of hydrostatic equilibration
    int phase2EndStep = 40000;       // N2: End of thermal equilibration
    int totalSteps = 100000;         // N_total: Total simulation duration

    // ====================================================
    // Stage 2: Thermal Collisions
    // ====================================================
    int thermalCollisionInterval = 10;          // N_therm: Steps between thermal events
    double thermalCollisionProbability = 0.1;   // p_therm: Probability of collision per event
    double thermalExchangeAlpha = 0.2;          // alpha_therm: Momentum exchange fraction (tune 0.1-0.2)

    // ====================================================
    // Stage 2: Thermal / Heating Parameters
    // ====================================================
    double baseTemperature = 1.0;                           // T_base: Baseline surface temperature
    double equatorPoleTemperatureContrast = 0.5;            // DeltaT: Contrast (0.5 * T_base)
    double solarFlux = 5000.0;                              // Q_solar: Energy input magnitude
    double verticalCoolingGamma = 0.2;                      // Gamma: Model-unit vertical lapse rate

    // ====================================================
    // Stage 2: Mechanics & Mode Flags
    // ====================================================
    double angularVelocity = 0.01;            // Omega: Planetary rotation (for later Coriolis/Solar logic)
    
    // false = use simplified latitude/altitude T_target model
    // true  = use full 3D solar-heating model (future stage)
    bool useFullSolarHeating = false;

    // ====================================================
    // Stage 3: Spherical Diagnostics
    // ====================================================
    // How often (in steps) to write particle_spherical_step_XXXXX.csv
    // after Stage 3 begins at phase2EndStep.
    int sphericalDiagnosticsInterval = 5000;

    // ====================================================
    // Stage 3: Circulation Accumulator
    // ====================================================
    int circulationLatitudeBins = 36;          // 5-degree bins from -90 to +90
    int circulationAltitudeBins = 20;          // altitude bins from 0 to atmosphereHeight
    int circulationAccumulationInterval = 10;  // accumulate every N steps
    int circulationOutputInterval = 5000;      // write circulation_accum CSV every N steps
    int circulationAverageStartStep = 50000;   // begin averaging after spin-up

    // If true, reset the accumulator after each write so each CSV represents
    // a fresh window rather than a growing cumulative average.
    bool resetCirculationAccumulatorAfterWrite = false;
};