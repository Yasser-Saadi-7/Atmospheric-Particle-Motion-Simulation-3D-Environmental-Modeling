#include "simulation/ThermalModel.h"
#include <cmath>
#include <algorithm>

ThermalModel::ThermalModel(const SimulationConfig& config) : config(config) {}

bool ThermalModel::shouldCollide(std::mt19937& rng) const {
    std::bernoulli_distribution dist(config.thermalCollisionProbability);
    return dist(rng);
}

Vec3 ThermalModel::sampleReservoirVelocity(double targetTemperature, double mass, std::mt19937& rng) const {
    // Safety check against unphysical states to prevent NaN from sqrt
    if (targetTemperature <= 0.0 || mass <= 0.0) {
        return Vec3(0.0, 0.0, 0.0);
    }

    double sigma_v = std::sqrt(targetTemperature / mass);
    std::normal_distribution<double> dist(0.0, sigma_v);

    return Vec3(dist(rng), dist(rng), dist(rng));
}

void ThermalModel::applyThermalCollision(Parcel& particle, const CoarseCellData& coarseCell, std::mt19937& rng) const {
    // 1. Identify coarse cell statistics
    Vec3 v_mean = coarseCell.meanVelocity;
    double T_target = coarseCell.targetTemperature;

    // 2. Compute thermal velocity in the flow rest frame (Galilean shift)
    Vec3 v_th = particle.v - v_mean;

    // 3. Sample a 3D reservoir velocity from a Maxwell-Boltzmann distribution at T_target
    Vec3 v_res = sampleReservoirVelocity(T_target, particle.mass, rng);

    // 4. Apply partial momentum exchange
    // Clamp alpha safely between 0 (no exchange) and 1 (full thermalization)
    double alpha = std::max(0.0, std::min(1.0, config.thermalExchangeAlpha));
    Vec3 v_th_new = v_th + (v_res - v_th) * alpha;

    // 5. Return to inertial frame
    particle.v = v_mean + v_th_new;

    // 6. Update particle temperature from thermal velocity relative to local mean flow
    // T_p = |v_th|^2 / 3.0 (model-unit kinetic temperature convention)
    double v_th_sq = v_th_new.x * v_th_new.x + v_th_new.y * v_th_new.y + v_th_new.z * v_th_new.z;
    particle.T_p = std::max(0.0, v_th_sq / 3.0);
}