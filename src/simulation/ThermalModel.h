#pragma once

#include <random>
#include "model/Vec3.h"
#include "model/Parcel.h"
#include "model/SimulationConfig.h"
#include "simulation/CoarseGrid.h"

class ThermalModel {
public:
    explicit ThermalModel(const SimulationConfig& config);

    // Determines if a collision should occur based on p_therm
    bool shouldCollide(std::mt19937& rng) const;

    // Samples a 3D velocity vector from a Maxwell-Boltzmann distribution
    Vec3 sampleReservoirVelocity(double targetTemperature, double mass, std::mt19937& rng) const;

    // Applies a single thermal collision event to the given particle
    void applyThermalCollision(Parcel& particle, const CoarseCellData& coarseCell, std::mt19937& rng) const;

private:
    SimulationConfig config;
};