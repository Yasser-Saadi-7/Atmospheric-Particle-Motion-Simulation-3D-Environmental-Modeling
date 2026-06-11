#include "SimulationEngine.h"
#include "analysis/Diagnostics.h"
#include <iostream>
#include <cmath>

SimulationEngine::SimulationEngine(const SimulationConfig& config)
    : config(config), currentStep(0), environment(config), thermalModel(config), fineGrid(config), coarseGrid(config), integrator(config), outputWriter("output") {
    rng.seed(42);
    circulationAccumulator.configure(this->config);
}

void SimulationEngine::initializeParticles() {
    std::cout << "Initializing " << config.numParticles << " particles..." << std::endl;
    parcels.reserve(config.numParticles);
    double initialTemp = config.initialTemperatureFactor * config.baseTemperature;

    for (int i = 0; i < config.numParticles; ++i) {
        Vec3 pos = sampleRandomPositionInShell();
        double mass = 1.0; 
        Vec3 vel = sampleInitialVelocity(initialTemp, mass);
        parcels.emplace_back(i, pos, vel, initialTemp, mass);
    }
    removeCenterOfMassDrift();
}

void SimulationEngine::run() {
    std::cout << "Starting Simulation..." << std::endl;
    runPhase1();
    runPhase2();
    runPhase3();
    std::cout << "Simulation run complete." << std::endl;
}

void SimulationEngine::runPhase1() {
    std::cout << "--- Entering Phase 1 (Hydrostatic Equilibrium) ---" << std::endl;
    fineGrid.build(parcels);
    integrator.initialize(parcels, fineGrid);
    
    auto initialEnergy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
    auto initialBounds = Diagnostics::checkShellBounds(parcels, config);
    outputWriter.appendSimulationLog(parcels, 0, initialEnergy, initialBounds);

    for (currentStep = 1; currentStep <= config.phase1EndStep; ++currentStep) {
        integrator.step(parcels, fineGrid);
        
        if (currentStep % 100 == 0) updateCoarseGrid();

        if (currentStep % config.logInterval == 0) {
            auto energy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
            auto bounds = Diagnostics::checkShellBounds(parcels, config);
            outputWriter.appendSimulationLog(parcels, currentStep, energy, bounds);
            
            // Log basic diagnostic
            logStage2Diagnostics();
        }

        if (currentStep % config.snapshotInterval == 0) {
            outputWriter.writeParticleSnapshot(parcels, currentStep);
            outputWriter.writeCoarseGridSnapshot(coarseGrid.getAllOccupiedCells(), currentStep);
        }

        if (currentStep % 2000 == 0) {
            std::cout << "Phase 1: Step " << currentStep << " / " << config.phase1EndStep 
                      << " | Sample altitude: " << (parcels[0].r.norm() - config.planetRadius) << std::endl;
        }
    }
}

void SimulationEngine::runPhase2() {
    std::cout << "--- Entering Phase 2 (Thermal Collisions & Target Temperatures) ---" << std::endl;
    config.dampingGamma = 0.0;

    integrator.setDamping(0.0);
    
    for (currentStep = config.phase1EndStep + 1; currentStep <= config.phase2EndStep; ++currentStep) {
        integrator.step(parcels, fineGrid);
        
        bool needsGridSync = (currentStep % 100 == 0) || (currentStep % config.thermalCollisionInterval == 0);
        if (needsGridSync) updateCoarseGrid();

        if (currentStep % config.thermalCollisionInterval == 0) applyThermalCollisions();

        if (currentStep % config.logInterval == 0) {
            auto energy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
            auto bounds = Diagnostics::checkShellBounds(parcels, config);
            outputWriter.appendSimulationLog(parcels, currentStep, energy, bounds);
            
            // Log Stage 2 temperature zones & validation summary
            logStage2Diagnostics();
        }

        if (currentStep % config.snapshotInterval == 0) {
            outputWriter.writeParticleSnapshot(parcels, currentStep);
            outputWriter.writeCoarseGridSnapshot(coarseGrid.getAllOccupiedCells(), currentStep);
            
            // Periodically save the altitude-temperature profile
            auto report = Diagnostics::computeStage2ValidationReport(coarseGrid, config);
            Diagnostics::saveAltitudeTemperatureProfile(report.altitudeTemperatureProfile, "output/altitude_temperature_profile.csv");
        }

        if (currentStep % 2000 == 0) {
            std::cout << "Phase 2: Step " << currentStep << " / " << config.phase2EndStep 
                      << " | Sample altitude: " << (parcels[0].r.norm() - config.planetRadius) << std::endl;
        }
    }
}

void SimulationEngine::runPhase3() {
    std::cout << "--- Entering Phase 3 (Rotation and Circulation) ---" << std::endl;

    // Activate the planetary rotational velocity exactly once at N2.
    // This seeds the inertial frame with the planet's spin; no explicit Coriolis
    // force is ever applied — meridional deflection emerges from the dynamics.
    if (!rotationActivated) {
        activateRotation();
        rotationActivated = true;
    }

    // Write spherical diagnostics for the rotation-activation snapshot at step N2.
    // This records the velocity field immediately after the rotational imprint.
    currentStep = config.phase2EndStep;
    outputWriter.writeParticleSphericalDiagnostics(
        parcels, currentStep, config.planetRadius, config.angularVelocity);

    for (currentStep = config.phase2EndStep + 1; currentStep <= config.totalSteps; ++currentStep) {
        integrator.step(parcels, fineGrid);

        bool needsGridSync = (currentStep % 100 == 0) || (currentStep % config.thermalCollisionInterval == 0);
        if (needsGridSync) updateCoarseGrid();

        if (currentStep % config.thermalCollisionInterval == 0) applyThermalCollisions();

        if (currentStep % config.logInterval == 0) {
            auto energy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
            auto bounds = Diagnostics::checkShellBounds(parcels, config);
            outputWriter.appendSimulationLog(parcels, currentStep, energy, bounds);
            logStage2Diagnostics();
        }

        if (currentStep % config.snapshotInterval == 0) {
            outputWriter.writeParticleSnapshot(parcels, currentStep);
            outputWriter.writeCoarseGridSnapshot(coarseGrid.getAllOccupiedCells(), currentStep);

            auto report = Diagnostics::computeStage2ValidationReport(coarseGrid, config);
            Diagnostics::saveAltitudeTemperatureProfile(report.altitudeTemperatureProfile, "output/altitude_temperature_profile.csv");
        }

        // Periodically write full per-particle spherical diagnostics after Stage 3 begins
        if (currentStep % config.sphericalDiagnosticsInterval == 0) {
            outputWriter.writeParticleSphericalDiagnostics(
                parcels, currentStep, config.planetRadius, config.angularVelocity);
        }

        // Announce once when circulation averaging begins
        if (!circulationLogPrinted && currentStep >= config.circulationAverageStartStep) {
            circulationLogPrinted = true;
            std::cout << "--- Stage 3 circulation accumulation started ---" << std::endl;
            std::cout << "Averaging from step: " << config.circulationAverageStartStep << std::endl;
            std::cout << "Latitude bins: "       << config.circulationLatitudeBins     << std::endl;
            std::cout << "Altitude bins: "       << config.circulationAltitudeBins     << std::endl;
        }

        // Accumulate longitude-averaged meridional mass flux for streamfunction preparation.
        // densityProxy * v_theta is the proxy for rho * v_theta needed for Psi (Sprint 4).
        if (currentStep >= config.circulationAverageStartStep &&
            currentStep % config.circulationAccumulationInterval == 0) {
            circulationAccumulator.accumulate(parcels, config, currentStep);
        }

        // Write time-averaged circulation diagnostics periodically
        if (currentStep >= config.circulationAverageStartStep &&
            currentStep % config.circulationOutputInterval == 0 &&
            circulationAccumulator.hasSamples()) {
            auto averages = circulationAccumulator.computeAverages(config);
            outputWriter.writeCirculationAverages(currentStep, averages);
            if (config.resetCirculationAccumulatorAfterWrite) {
                circulationAccumulator.reset();
            }
        }

        if (currentStep % 2000 == 0) {
            std::cout << "Phase 3: Step " << currentStep << " / " << config.totalSteps
                      << " | Sample altitude: " << (parcels[0].r.norm() - config.planetRadius) << std::endl;
        }
    }
}

void SimulationEngine::activateRotation() {
    // Safety check: rotation must not already be active
    if (rotationActivated) {
        std::cerr << "[WARNING] activateRotation() called more than once — skipping." << std::endl;
        return;
    }

    // Compute mean speed before imprinting the rotational velocity
    double meanSpeedBefore = 0.0;
    for (const auto& p : parcels) {
        meanSpeedBefore += p.v.norm();
    }
    if (!parcels.empty()) meanSpeedBefore /= static_cast<double>(parcels.size());

    std::cout << "Rotation activated once at step " << config.phase2EndStep << std::endl;
    std::cout << "Omega = " << config.angularVelocity << std::endl;
    std::cout << "Mean speed before rotation: " << meanSpeedBefore << std::endl;

    // Imprint v += Omega x r (rotation about z-axis) onto every particle.
    // vx -= Omega * y
    // vy += Omega * x
    // vz unchanged
    for (auto& p : parcels) {
        p.v.x -= config.angularVelocity * p.r.y;
        p.v.y += config.angularVelocity * p.r.x;
    }

    // Compute mean speed after imprint to verify the velocity field changed
    double meanSpeedAfter = 0.0;
    for (const auto& p : parcels) {
        meanSpeedAfter += p.v.norm();
    }
    if (!parcels.empty()) meanSpeedAfter /= static_cast<double>(parcels.size());

    std::cout << "Mean speed after rotation:  " << meanSpeedAfter << std::endl;
}

void SimulationEngine::logStage2Diagnostics() {
    // Generate full Stage 2 report from the Diagnostics layer
    auto report = Diagnostics::computeStage2ValidationReport(coarseGrid, config);

    // Pass data to OutputWriter
    outputWriter.appendTemperatureZoneLog(
        currentStep, 
        report.zoneTemperatures.equatorialMean, 
        report.zoneTemperatures.midLatitudeMean, 
        report.zoneTemperatures.polarMean
    );

    // If we are in Phase 2, optionally print a compact status to watch the physics align
    if (currentStep >= config.phase1EndStep && currentStep % 5000 == 0) {
        std::cout << "  -> Stage 2 Diagnostics [Step " << currentStep << "]:" << std::endl;
        std::cout << "     T_Eq: " << report.zoneTemperatures.equatorialMean 
                  << " | T_Polar: " << report.zoneTemperatures.polarMean 
                  << " -> Valid: " << (report.equatorWarmerThanPolar ? "YES" : "NO") << std::endl;
        std::cout << "     Eq Upwelling <v_r>: " << report.equatorialRadialVelocity.meanRadialVelocity 
                  << " -> Valid: " << (report.positiveEquatorialUpwelling ? "YES" : "NO") << std::endl;
    }
}

void SimulationEngine::applyThermalCollisions() {
    for (auto& p : parcels) {
        if (thermalModel.shouldCollide(rng)) {
            // Find the particle's macroscopic cell
            CoarseCellIndex idx = coarseGrid.positionToCell(p.r);
            const CoarseCellData* cellData = coarseGrid.getCellData(idx);
            
            // Apply collision safely if the cell is correctly registered
            if (cellData != nullptr) {
                thermalModel.applyThermalCollision(p, *cellData, rng);
            }
        }
    }
}

void SimulationEngine::validateStage1() {
    // ... [Content remains exactly as previously implemented in previous step]
    std::cout << "\n=======================================================\n";
    std::cout << "          STAGE 1 VERIFICATION & LOCK PROTOCOL           \n";
    std::cout << "=======================================================\n";
    
    std::cout << "\n[1/3] Equilibrating system (running standard Phase 1)...\n";
    runPhase1();
    
    std::cout << "\n[2/3] Validating Spatial Constraints & Density...\n";
    auto bounds = Diagnostics::checkShellBounds(parcels, config);
    std::cout << "  - Shell Bounds Check: " << (bounds.allInside ? "PASS" : "FAIL") << "\n";
    
    auto profile = Diagnostics::computeRadialDensityProfile(parcels, config, 20); 
    auto densityVal = Diagnostics::validateDensityProfile(profile, 0.20); 
    std::cout << "  - Radial Density Monotonicity: " << (densityVal.isApproximatelyMonotonic ? "PASS" : "FAIL") << "\n";
    
    std::cout << "\n[3/3] Validating Energy Conservation (1000 steps, NO Damping)...\n";
    double oldGamma = config.dampingGamma;
    config.dampingGamma = 0.0; 
    
    double initialTotalEnergy = Diagnostics::computeEnergyReport(parcels, fineGrid, config).total;
    double maxDrift = 0.0;
    
    for (int i = 1; i <= 1000; ++i) {
        integrator.step(parcels, fineGrid);
        double currentEnergy = Diagnostics::computeEnergyReport(parcels, fineGrid, config).total;
        double drift = std::abs((currentEnergy - initialTotalEnergy) / (std::abs(initialTotalEnergy) + 1e-9));
        if (drift > maxDrift) maxDrift = drift;
    }
    
    config.dampingGamma = oldGamma; 
    std::cout << "  - Energy Conservation Test: " << (maxDrift <= 0.01 ? "PASS" : "FAIL") << "\n";
}

void SimulationEngine::updateCoarseGrid() { 
    coarseGrid.build(parcels, environment); 
}

Vec3 SimulationEngine::sampleRandomPositionInShell() {
    std::uniform_real_distribution<double> distU(0.0, 1.0);
    std::uniform_real_distribution<double> distCos(-1.0, 1.0);
    std::uniform_real_distribution<double> distPhi(0.0, 2.0 * M_PI);

    double R3 = std::pow(config.planetRadius, 3);
    double outerR3 = std::pow(config.planetRadius + config.atmosphereHeight, 3);
    double u = distU(rng);
    double r = std::cbrt(R3 + u * (outerR3 - R3));

    double cosTheta = distCos(rng);
    double sinTheta = std::sqrt(1.0 - cosTheta * cosTheta);
    double phi = distPhi(rng);
    return Vec3(r * sinTheta * std::cos(phi), r * sinTheta * std::sin(phi), r * cosTheta);
}

Vec3 SimulationEngine::sampleInitialVelocity(double temperature, double mass) {
    double stddev = std::sqrt(temperature / mass);
    std::normal_distribution<double> distN(0.0, stddev);
    return Vec3(distN(rng), distN(rng), distN(rng));
}

void SimulationEngine::removeCenterOfMassDrift() {
    Vec3 totalMomentum(0, 0, 0);
    double totalMass = 0.0;
    for (const auto& p : parcels) {
        totalMomentum += p.v * p.mass;
        totalMass += p.mass;
    }
    if (totalMass > 0.0) {
        Vec3 comVelocity = totalMomentum / totalMass;
        for (auto& p : parcels) { p.v -= comVelocity; }
    }
}