#include <iostream>
#include "simulation/SimulationEngine.h"

int main() {
    std::cout << "Atmospheric Simulation Project Started\n";

    SimulationEngine engine;
    engine.run();

    return 0;
}