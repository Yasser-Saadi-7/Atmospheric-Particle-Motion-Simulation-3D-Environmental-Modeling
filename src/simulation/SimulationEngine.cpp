#include "SimulationEngine.h"
#include <iostream>

SimulationEngine::SimulationEngine() {
    initializeParcels();
}

void SimulationEngine::initializeParcels() {
    parcels.resize(config.numberOfParcels);

    for (int i = 0; i < config.numberOfParcels; i++) {
        parcels[i].position.z = 100.0 + i;
        parcels[i].velocity = {0.0, 0.0, 0.0};
    }
}

void SimulationEngine::run() {
    std::cout << "Simulation started with "
              << parcels.size()
              << " parcels\n";

    for (int step = 0; step < config.totalSteps; step++) {
        std::cout << "Step: " << step << "\n";
    }

    std::cout << "Simulation finished\n";
}