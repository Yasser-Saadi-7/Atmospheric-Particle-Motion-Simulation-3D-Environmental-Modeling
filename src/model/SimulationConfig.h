#ifndef SIMULATION_CONFIG_H
#define SIMULATION_CONFIG_H

struct SimulationConfig {
    double dt = 0.01;
    int totalSteps = 100;
    int numberOfParcels = 10;
};

#endif