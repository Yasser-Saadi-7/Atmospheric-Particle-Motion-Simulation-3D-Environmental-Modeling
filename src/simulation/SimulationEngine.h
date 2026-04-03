#ifndef SIMULATION_ENGINE_H
#define SIMULATION_ENGINE_H

#include <vector>
#include "../model/Parcel.h"
#include "../model/SimulationConfig.h"

class SimulationEngine {
private:
    std::vector<Parcel> parcels;
    SimulationConfig config;

    void initializeParcels();

public:
    SimulationEngine();
    void run();
};

#endif