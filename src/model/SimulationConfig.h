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

    // ====================================================
    // Stage 3: Streamfunction (Psi)
    // ====================================================
    // How often to write streamfunction_step_XXXXX.csv (and circulation CSV).
    // Combined trigger for both outputs to keep them in sync.
    int streamfunctionOutputInterval = 5000;

    // If true, streamfunction is computed and written whenever circulation
    // averages are written (they share the same output trigger above).
    bool writeStreamfunctionAfterCirculationOutput = true;

    // Optional: minimum absolute mass-flux threshold.
    // Reserved for future filtering; not applied to the integration itself.
    double streamfunctionMinMassFluxThreshold = 0.0;

    // ====================================================
    // Stage 4 Sprint 4.1: Moisture State
    // ====================================================
    // Activate the moisture state (q_p carried by each particle).
    bool enableMoisture = true;

    // Near-surface specific humidity [kg/kg].
    double initialSurfaceSpecificHumidity = 0.015;

    // Fraction of atmosphereHeight defining the lower constant-humidity layer.
    // Particles below (humiditySurfaceLayerFraction * H) receive the surface value.
    double humiditySurfaceLayerFraction = 0.20;

    // Exponential decay scale as a fraction of atmosphereHeight.
    // Controls how quickly q_p falls off above the lower layer.
    double humidityDecayScaleFraction = 0.30;

    // ====================================================
    // Stage 4 Sprint 4.2: Saturation Physics Scaling
    // ====================================================
    // Enables the saturation physics module (q_sat computations).
    bool enableMoisturePhysics = true;

    // Model temperature unit that maps to referenceKelvinTemperature.
    double referenceModelTemperature = 1.0;

    // Physical temperature [K] corresponding to referenceModelTemperature.
    double referenceKelvinTemperature = 300.0;

    // Kelvin change per model temperature unit: T_K = T_ref_K + scale * (T_model - T_ref_model).
    double modelTemperatureKelvinScale = 50.0;

    // Physical height [m] of the full atmosphere (maps to atmosphereHeight model units).
    double atmospherePhysicalHeightMeters = 20000.0;

    // Sea-level atmospheric pressure [Pa].
    double seaLevelPressurePa = 101325.0;

    // Pressure scale height [m] for the exponential profile: p(h) = p0 * exp(-h / H_scale).
    double pressureScaleHeightMeters = 8500.0;

    // Safety clamp bounds for physical temperature [K].
    double minPhysicalTemperatureK = 180.0;
    double maxPhysicalTemperatureK = 330.0;

    // Safety clamp bounds for specific humidity [kg/kg].
    double minSpecificHumidity = 0.0;
    double maxSpecificHumidity = 0.05;

    // ====================================================
    // Stage 4 Sprint 4.4: Humidity Mixing During Collisions
    // ====================================================
    // If true, q_p is nudged toward q_mean_cell during thermal collision events.
    bool enableHumidityMixing = true;

    // Humidity exchange fraction per collision event.
    // Negative sentinel value means: inherit thermalExchangeAlpha at runtime.
    double humidityMixingAlpha = -1.0;

    // ====================================================
    // Stage 4 Sprint 4.5: Condensation and Latent Heat
    // ====================================================
    // Enable condensation: when q_p > q_sat, condense excess and release latent heat.
    bool enableCondensation = true;

    // Model-scaled latent heating coefficient [model-T / (kg/kg)].
    // Physical Lv/cp is NOT used directly because T_p is in model units.
    double latentHeatModelFactor = 0.05;

    // Maximum condensation amount removed from q_p per particle per step [kg/kg].
    double maxCondensationDeltaQPerStep = 1e-4;

    // Supersaturation threshold: condensation fires only when q_p > q_sat + tolerance.
    double supersaturationTolerance = 1e-10;

    // ====================================================
    // Stage 4 Sprint 4.6: Near-Surface Evaporation
    // ====================================================
    // Enable near-surface evaporation: when q_p < q_sat in the lower layer, add vapor.
    bool enableEvaporation = true;

    // Lower layer fraction: h_evap = evaporationLayerFraction * atmosphereHeight.
    double evaporationLayerFraction = 0.15;

    // Evaporation rate coefficient k_evap [1/time-unit].
    double evaporationRate = 0.001;

    // Safety clamp: maximum vapor added to q_p per particle per step [kg/kg].
    double maxEvaporationDeltaQPerStep = 1e-5;

    // ====================================================
    // Stage 4 Sprint 4.7: Water Balance Logging
    // ====================================================
    // Enable moisture_balance.csv output and water balance diagnostics.
    bool enableWaterBalanceLogging = true;

    // Absolute error threshold: |total_q - expected_q| <= this → PASS.
    double waterBalanceToleranceAbs = 1e-8;

    // Relative error threshold: |error / expected| <= this → PASS.
    double waterBalanceToleranceRel = 1e-6;
};