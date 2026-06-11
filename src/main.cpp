#include <iostream>
#include "model/SimulationConfig.h"
#include "simulation/SimulationEngine.h"

int main() {
    std::cout << "--- Atmospheric Simulation Project (Stage 2) ---" << std::endl;

    SimulationConfig config;
    SimulationEngine engine(config);
    
    engine.initializeParticles();
    
    // Phase 1 (Equilibration) -> Phase 2 (Thermal Dynamics)
    engine.run();

    return 0;
}