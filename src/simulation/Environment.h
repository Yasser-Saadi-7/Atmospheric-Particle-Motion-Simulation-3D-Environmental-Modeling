#pragma once

#include "model/Vec3.h"
#include "model/SimulationConfig.h"

class Environment {
public:
    explicit Environment(const SimulationConfig& config);

    // ----------------------------------------------------
    // Geometric Helpers
    // ----------------------------------------------------
    double computeRadius(const Vec3& position) const;
    
    // Computes altitude above planet surface (h = r - R)
    double computeAltitude(const Vec3& position) const;
    
    // Computes latitude theta = asin(z / r). Returns radians [-pi/2, pi/2]
    double computeLatitudeRadians(const Vec3& position) const;

    // ----------------------------------------------------
    // Stage 2: Thermal Model
    // ----------------------------------------------------
    // Computes the idealized temperature for a given location using the formula:
    // T_target(theta) = T_base + DeltaT * cos^2(theta) - Gamma * (h / H)
    double computeTargetTemperatureSimplified(const Vec3& cellCenter) const;

private:
    SimulationConfig config;
};