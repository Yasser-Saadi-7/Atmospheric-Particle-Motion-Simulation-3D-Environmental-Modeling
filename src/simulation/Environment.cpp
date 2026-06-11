#include "simulation/Environment.h"
#include <cmath>
#include <algorithm>

Environment::Environment(const SimulationConfig& config) : config(config) {}

double Environment::computeRadius(const Vec3& position) const {
    return position.norm();
}

double Environment::computeAltitude(const Vec3& position) const {
    double r = computeRadius(position);
    double h = r - config.planetRadius;
    
    // Clamp slightly negative values arising from numerical boundary integration noise
    return std::max(0.0, h);
}

double Environment::computeLatitudeRadians(const Vec3& position) const {
    double r = computeRadius(position);
    
    // Safe-guard against division by zero at the exact center of the coordinate system
    if (r < 1e-9) {
        return 0.0; 
    }
    
    double z_ratio = position.z / r;
    
    // Clamp to [-1.0, 1.0] to prevent NaN in asin due to floating point inaccuracies
    z_ratio = std::max(-1.0, std::min(1.0, z_ratio));
    
    return std::asin(z_ratio);
}

double Environment::computeTargetTemperatureSimplified(const Vec3& cellCenter) const {
    double h = computeAltitude(cellCenter);
    double theta = computeLatitudeRadians(cellCenter);

    // Fetch Stage 2 parameters from config
    double T_base = config.baseTemperature;
    double deltaT = config.equatorPoleTemperatureContrast;
    double gamma = config.verticalCoolingGamma;
    double H = config.atmosphereHeight;

    double cos_theta = std::cos(theta);
    
    // Compute latitude-dependent heating and altitude-dependent cooling
    double T_target = T_base + deltaT * (cos_theta * cos_theta) - gamma * (h / H);

    // Ensure temperature never drops below absolute zero in the model limits
    return std::max(0.0, T_target);
}