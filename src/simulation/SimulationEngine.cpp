#include "SimulationEngine.h"
#include "analysis/Diagnostics.h"
#include "simulation/MoistureModel.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <numeric>

SimulationEngine::SimulationEngine(const SimulationConfig& config)
    : config(config), currentStep(0), environment(config), thermalModel(config), fineGrid(config), coarseGrid(config), integrator(config), outputWriter("output") {
    rng.seed(42);
    circulationAccumulator.configure(this->config);

    // Stage 4 Sprint 4.2: run saturation physics self-test exactly once at startup.
    if (this->config.enableMoisturePhysics) {
        MoistureModel::runSaturationSelfTest(this->config);
    }

    // Stage 4 Sprint 4.4: humidity mixing banner.
    if (this->config.enableHumidityMixing) {
        double effectiveAlpha = (this->config.humidityMixingAlpha >= 0.0)
                                ? this->config.humidityMixingAlpha
                                : this->config.thermalExchangeAlpha;
        std::cout << "--- Stage 4 Sprint 4.4 humidity mixing enabled during thermal collisions ---" << std::endl;
        std::cout << "  Humidity mixing alpha = " << effectiveAlpha << std::endl;
        std::cout << "  q_p nudged toward q_mean_cell on each thermal collision event" << std::endl;
    }

    // Stage 4 Sprint 4.5: condensation banner.
    if (this->config.enableCondensation) {
        std::cout << "--- Stage 4 Sprint 4.5 condensation enabled ---" << std::endl;
        std::cout << "  Latent heat model factor        = " << this->config.latentHeatModelFactor << std::endl;
        std::cout << "  Max condensation dq per step    = " << this->config.maxCondensationDeltaQPerStep << std::endl;
        std::cout << "  Supersaturation tolerance       = " << this->config.supersaturationTolerance << std::endl;
    }

    // Stage 4 Sprint 4.6: evaporation banner.
    if (this->config.enableEvaporation) {
        std::cout << "--- Stage 4 Sprint 4.6 evaporation enabled ---" << std::endl;
        std::cout << "  Evaporation layer fraction      = " << this->config.evaporationLayerFraction << std::endl;
        std::cout << "  Evaporation rate                = " << this->config.evaporationRate << std::endl;
        std::cout << "  Max evaporation dq per step     = " << this->config.maxEvaporationDeltaQPerStep << std::endl;
    }

    // Stage 4 Sprint 4.7: water balance banner.
    if (this->config.enableWaterBalanceLogging) {
        std::cout << "--- Stage 4 Sprint 4.7 water balance logging enabled ---" << std::endl;
    }
}

void SimulationEngine::initializeParticles() {
    std::cout << "Initializing " << config.numParticles << " particles..." << std::endl;
    parcels.reserve(config.numParticles);
    double initialTemp = config.initialTemperatureFactor * config.baseTemperature;

    const double H        = config.atmosphereHeight;
    const double q_surf   = config.initialSurfaceSpecificHumidity;
    const double frac_low = config.humiditySurfaceLayerFraction;
    const double frac_dec = config.humidityDecayScaleFraction;
    const double alt_low  = frac_low * H;
    const double scale_h  = frac_dec * H;

    for (int i = 0; i < config.numParticles; ++i) {
        Vec3 pos = sampleRandomPositionInShell();
        double mass = 1.0; 
        Vec3 vel = sampleInitialVelocity(initialTemp, mass);
        parcels.emplace_back(i, pos, vel, initialTemp, mass);

        // Stage 4 Sprint 4.1: initialize specific humidity q_p.
        if (config.enableMoisture) {
            double radius   = pos.norm();
            double altitude = radius - config.planetRadius;
            double q_p;

            if (altitude < alt_low) {
                q_p = q_surf;
            } else {
                q_p = q_surf * std::exp(-(altitude - alt_low) / scale_h);
            }

            // Clamp: must be finite, non-negative, and physically bounded.
            if (!std::isfinite(q_p) || q_p < 0.0) q_p = 0.0;
            q_p = std::min(q_p, 0.05);

            parcels.back().specificHumidity = q_p;
        }
    }
    removeCenterOfMassDrift();

    // Stage 4 Sprint 4.1 startup log
    if (config.enableMoisture) {
        double q_min  =  1e30;
        double q_max  = -1e30;
        double q_sum  =  0.0;
        for (const auto& p : parcels) {
            q_min  = std::min(q_min, p.specificHumidity);
            q_max  = std::max(q_max, p.specificHumidity);
            q_sum += p.specificHumidity;
        }
        double q_mean = parcels.empty() ? 0.0 : q_sum / static_cast<double>(parcels.size());

        std::cout << "--- Stage 4 Sprint 4.1 moisture state enabled ---" << std::endl;
        std::cout << "  Initial q_p near surface = " << q_surf << std::endl;
        std::cout << "  Humidity initialization: lower-layer constant, exponential decay above" << std::endl;
        std::cout << "  Initial humidity stats: min_q=" << q_min
                  << ", max_q=" << q_max
                  << ", mean_q=" << q_mean << std::endl;
    }

    // Stage 4 Sprint 4.7: record initial total humidity once for water balance accounting.
    if (config.enableWaterBalanceLogging && !waterBalanceInitialized) {
        initialTotalSpecificHumidity = computeTotalSpecificHumidity();
        waterBalanceInitialized = true;
        std::cout << "--- Stage 4 Sprint 4.7 water balance initialized ---" << std::endl;
        std::cout << "  Initial total q = " << initialTotalSpecificHumidity << std::endl;
    }
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

        applyNearSurfaceEvaporation();
        applyCondensation();

        if (currentStep % config.logInterval == 0) {
            auto energy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
            auto bounds = Diagnostics::checkShellBounds(parcels, config);
            outputWriter.appendSimulationLog(parcels, currentStep, energy, bounds);
            
            // Log basic diagnostic
            logStage2Diagnostics();

            // Stage 4 Sprint 4.5: condensation log.
            if (config.enableCondensation) {
                outputWriter.appendCondensationLog(currentStep,
                    condensationThisStep, cumulativeCondensation,
                    latentHeatingThisStep, cumulativeLatentHeating,
                    condensationEventsThisStep, cumulativeCondensationEvents);
                condensationThisStep        = 0.0;
                latentHeatingThisStep       = 0.0;
                condensationEventsThisStep  = 0;
            }

            // Stage 4 Sprint 4.6: evaporation log.
            if (config.enableEvaporation) {
                outputWriter.appendEvaporationLog(currentStep,
                    evaporationThisStep, cumulativeEvaporation,
                    evaporationEventsThisStep, cumulativeEvaporationEvents);
                evaporationThisStep         = 0.0;
                evaporationEventsThisStep   = 0;
            }

            // Stage 4 Sprint 4.7: water balance.
            updateWaterBalanceDiagnostics(currentStep);
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

        applyNearSurfaceEvaporation();
        applyCondensation();

        if (currentStep % config.logInterval == 0) {
            auto energy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
            auto bounds = Diagnostics::checkShellBounds(parcels, config);
            outputWriter.appendSimulationLog(parcels, currentStep, energy, bounds);
            
            // Log Stage 2 temperature zones & validation summary
            logStage2Diagnostics();

            // Stage 4 Sprint 4.5: condensation log.
            if (config.enableCondensation) {
                outputWriter.appendCondensationLog(currentStep,
                    condensationThisStep, cumulativeCondensation,
                    latentHeatingThisStep, cumulativeLatentHeating,
                    condensationEventsThisStep, cumulativeCondensationEvents);
                condensationThisStep        = 0.0;
                latentHeatingThisStep       = 0.0;
                condensationEventsThisStep  = 0;
            }

            // Stage 4 Sprint 4.6: evaporation log.
            if (config.enableEvaporation) {
                outputWriter.appendEvaporationLog(currentStep,
                    evaporationThisStep, cumulativeEvaporation,
                    evaporationEventsThisStep, cumulativeEvaporationEvents);
                evaporationThisStep         = 0.0;
                evaporationEventsThisStep   = 0;
            }

            // Stage 4 Sprint 4.7: water balance.
            updateWaterBalanceDiagnostics(currentStep);
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

        applyNearSurfaceEvaporation();
        applyCondensation();

        if (currentStep % config.logInterval == 0) {
            auto energy = Diagnostics::computeEnergyReport(parcels, fineGrid, config);
            auto bounds = Diagnostics::checkShellBounds(parcels, config);
            outputWriter.appendSimulationLog(parcels, currentStep, energy, bounds);
            logStage2Diagnostics();

            // Stage 4 Sprint 4.5: condensation log.
            if (config.enableCondensation) {
                outputWriter.appendCondensationLog(currentStep,
                    condensationThisStep, cumulativeCondensation,
                    latentHeatingThisStep, cumulativeLatentHeating,
                    condensationEventsThisStep, cumulativeCondensationEvents);
                condensationThisStep        = 0.0;
                latentHeatingThisStep       = 0.0;
                condensationEventsThisStep  = 0;
            }

            // Stage 4 Sprint 4.6: evaporation log.
            if (config.enableEvaporation) {
                outputWriter.appendEvaporationLog(currentStep,
                    evaporationThisStep, cumulativeEvaporation,
                    evaporationEventsThisStep, cumulativeEvaporationEvents);
                evaporationThisStep         = 0.0;
                evaporationEventsThisStep   = 0;
            }

            // Stage 4 Sprint 4.7: water balance.
            updateWaterBalanceDiagnostics(currentStep);
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

        // Write circulation averages and streamfunction together.
        // Both share the same output interval so the CSV files stay in sync.
        if (currentStep >= config.circulationAverageStartStep &&
            currentStep % config.streamfunctionOutputInterval == 0 &&
            circulationAccumulator.hasSamples()) {

            // One-time announcement when streamfunction diagnostics first fire
            if (!streamfunctionLogPrinted) {
                streamfunctionLogPrinted = true;
                std::cout << "--- Stage 3 streamfunction diagnostics started ---" << std::endl;
                std::cout << "Computing Psi from time-averaged mean_mass_flux" << std::endl;
                std::cout << "Latitude bins: " << config.circulationLatitudeBins << std::endl;
                std::cout << "Altitude bins: " << config.circulationAltitudeBins << std::endl;
            }

            auto averages = circulationAccumulator.computeAverages(config);
            outputWriter.writeCirculationAverages(currentStep, averages);

            if (config.writeStreamfunctionAfterCirculationOutput) {
                // Integrate mean_mass_flux upward to obtain Psi(lat, alt).
                // Psi is not computed from raw particles — only from the
                // time-averaged, longitude-collapsed mass flux grid.
                auto psiCells   = streamfunctionCalculator.compute(averages, config);
                auto psiSummary = streamfunctionCalculator.summarize(psiCells);
                outputWriter.writeStreamfunction(currentStep, psiCells, psiSummary);
            }

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

void SimulationEngine::applyCondensation() {
    if (!config.enableCondensation) return;

    for (auto& p : parcels) {
        // Compute model altitude (clamped to zero if underground due to boundary bounce).
        double radius   = p.r.norm();
        double altitude = radius - config.planetRadius;
        if (altitude < 0.0) altitude = 0.0;

        // Saturation specific humidity at current model temperature and altitude.
        double q_sat = MoistureModel::saturationSpecificHumidity(p.T_p, altitude, config);

        // Skip particle if q_sat is invalid or non-positive.
        if (!std::isfinite(q_sat) || q_sat <= 0.0) continue;

        // Repair q_p if it has become non-finite.
        if (!std::isfinite(p.specificHumidity)) p.specificHumidity = 0.0;

        // No condensation unless clearly supersaturated.
        if (p.specificHumidity <= q_sat + config.supersaturationTolerance) continue;

        double raw_dq = p.specificHumidity - q_sat;
        double dq     = std::min(raw_dq, config.maxCondensationDeltaQPerStep);
        dq = std::max(dq, 0.0);

        double T_prev = p.T_p;

        p.specificHumidity -= dq;
        // Model-scaled latent heating. Physical Lv/cp is not used directly because T_p is in model units.
        p.T_p += config.latentHeatModelFactor * dq;

        // Clamp q_p.
        if (!std::isfinite(p.specificHumidity) || p.specificHumidity < 0.0) p.specificHumidity = 0.0;
        if (p.specificHumidity > config.maxSpecificHumidity) p.specificHumidity = config.maxSpecificHumidity;

        // Clamp T_p: restore if non-finite, otherwise just guard against negative.
        if (!std::isfinite(p.T_p)) p.T_p = T_prev;
        if (p.T_p < 0.0) p.T_p = 0.0;

        if (dq > 0.0) {
            condensationThisStep         += dq;
            cumulativeCondensation       += dq;
            latentHeatingThisStep        += config.latentHeatModelFactor * dq;
            cumulativeLatentHeating      += config.latentHeatModelFactor * dq;
            ++condensationEventsThisStep;
            ++cumulativeCondensationEvents;
        }
    }
}

void SimulationEngine::applyNearSurfaceEvaporation() {
    if (!config.enableEvaporation) return;

    const double evapLayerHeight = config.evaporationLayerFraction * config.atmosphereHeight;

    for (auto& p : parcels) {
        double radius   = p.r.norm();
        double altitude = radius - config.planetRadius;
        if (altitude < 0.0) altitude = 0.0;

        // Only apply evaporation in the near-surface lower layer.
        if (altitude >= evapLayerHeight) continue;

        // Sprint 4.6: using particle.temperature as a local near-surface evaporation temperature proxy.
        // A later refinement may use surface temperature T_surface(theta) or T_target.
        double q_sat = MoistureModel::saturationSpecificHumidity(p.T_p, altitude, config);

        if (!std::isfinite(q_sat) || q_sat <= 0.0) continue;

        if (!std::isfinite(p.specificHumidity)) p.specificHumidity = 0.0;

        // Evaporation only occurs when the particle is subsaturated.
        double humidityDeficit = q_sat - p.specificHumidity;
        if (humidityDeficit <= 0.0) continue;

        double dq = config.evaporationRate * humidityDeficit * config.dt;
        dq = std::clamp(dq, 0.0, config.maxEvaporationDeltaQPerStep);

        // Do not push q_p above maxSpecificHumidity.
        double room = config.maxSpecificHumidity - p.specificHumidity;
        if (room <= 0.0) continue;
        dq = std::min(dq, room);
        dq = std::max(dq, 0.0);

        p.specificHumidity += dq;

        // Safety clamp.
        if (!std::isfinite(p.specificHumidity) || p.specificHumidity < 0.0) p.specificHumidity = 0.0;
        if (p.specificHumidity > config.maxSpecificHumidity) p.specificHumidity = config.maxSpecificHumidity;

        if (dq > 0.0) {
            evaporationThisStep         += dq;
            cumulativeEvaporation       += dq;
            ++evaporationEventsThisStep;
            ++cumulativeEvaporationEvents;
        }
    }
}

double SimulationEngine::computeTotalSpecificHumidity() const {
    double total = 0.0;
    for (const auto& p : parcels) {
        if (std::isfinite(p.specificHumidity) && p.specificHumidity >= 0.0) {
            total += p.specificHumidity;
        }
    }
    return total;
}

void SimulationEngine::updateWaterBalanceDiagnostics(int step) {
    if (!config.enableWaterBalanceLogging) return;

    currentTotalSpecificHumidity = computeTotalSpecificHumidity();

    waterBalanceExpected = initialTotalSpecificHumidity
                         + cumulativeEvaporation
                         - cumulativeCondensation;

    waterBalanceError = currentTotalSpecificHumidity - waterBalanceExpected;

    double denom = std::max(std::abs(waterBalanceExpected), 1e-12);
    waterBalanceRelativeError = waterBalanceError / denom;

    std::string status;
    if (!std::isfinite(waterBalanceError) || !std::isfinite(waterBalanceRelativeError)) {
        status = "WARNING";
    } else if (std::abs(waterBalanceError) <= config.waterBalanceToleranceAbs ||
               std::abs(waterBalanceRelativeError) <= config.waterBalanceToleranceRel) {
        status = "PASS";
    } else {
        status = "WARNING";
    }

    outputWriter.appendMoistureBalanceLog(step,
        currentTotalSpecificHumidity,
        initialTotalSpecificHumidity,
        cumulativeEvaporation,
        cumulativeCondensation,
        waterBalanceExpected,
        waterBalanceError,
        waterBalanceRelativeError,
        status);
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