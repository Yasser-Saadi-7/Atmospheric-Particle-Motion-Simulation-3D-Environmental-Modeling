#pragma once

#include <vector>
#include "model/Parcel.h"
#include "model/SimulationConfig.h"
#include "simulation/FineGrid.h"
#include "simulation/BoundaryHandler.h"

class Integrator {
public:
    Integrator(const SimulationConfig& config);

    // Computes initial accelerations at t=0 before the simulation loop begins
    void initialize(std::vector<Parcel>& parcels, const FineGrid& fineGrid);

    // Performs one full Velocity Verlet integration step
    void step(std::vector<Parcel>& parcels, FineGrid& fineGrid);

    // Updates the damping factor dynamically during the simulation
    void setDamping(double newGamma);

private:
    SimulationConfig config;
    BoundaryHandler boundaryHandler;

    // Evaluates Stage 1 forces and updates particle accelerations
    void computeForces(std::vector<Parcel>& parcels, const FineGrid& fineGrid);
};