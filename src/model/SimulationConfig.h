#pragma once

struct SimulationConfig {
    // ----------------------------------------------------
    // General Simulation Parameters
    // ----------------------------------------------------
    int numParticles = 10000;              // Recommended range: 5000 to 20000
    double dt = 0.01;                      // Time step

    // ----------------------------------------------------
    // Geometric Parameters
    // ----------------------------------------------------
    double planetRadius = 50.0;            // R: Inner radius of the shell
    double atmosphereHeight = 20.0;        // H: Thickness of the atmosphere

    // ----------------------------------------------------
    // Physical & Thermodynamic Parameters
    // ----------------------------------------------------
    double gravity = 0.016;                // g: Gravitational acceleration
    double baseTemperature = 1.0;          // T_base: Reference temperature (model units)
    double initialTemperatureFactor = 0.1; // Initialize particles at (0.1 * T_base)

    // ----------------------------------------------------
    // Interaction & Force Parameters
    // ----------------------------------------------------
    double sigma = 2.0;                    // Particle diameter
    double cutoffRadius = 2.0;             // r_c: Force cutoff distance (matches sigma)
    double repulsionStiffness = 200.0;     // k: Soft-sphere contact repulsion stiffness
    double maxForce = 100.0;               // F_max: Force limiter to prevent numerical blow-up

    // ----------------------------------------------------
    // Phase 1 Specific Parameters (Hydrostatic Equilibrium)
    // ----------------------------------------------------
    int phase1Steps = 20000;               // N1: Duration of Phase 1
    double dampingGamma = 100.0;           // γ_max: Damping coefficient to drive equilibrium

    // ----------------------------------------------------
    // Boundary Conditions
    // ----------------------------------------------------
    double elasticityInner = 0.8;          // Reflection elasticity at planet surface (r = R)
    double elasticityOuter = 0.5;          // Reflection elasticity at top of atmosphere (r = R + H)
};