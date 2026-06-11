#pragma once

#include <vector>
#include "model/Vec3.h"
#include "model/Parcel.h"
#include "model/SimulationConfig.h"

class BoundaryHandler {
public:
    BoundaryHandler(const SimulationConfig& config);

    // Enforces boundary conditions on a single particle
    void apply(Parcel& p) const;

    // Enforces boundary conditions on an entire vector of particles
    void applyAll(std::vector<Parcel>& parcels) const;

private:
    double rInner;
    double rOuter;
    double elasticityInner;
    double elasticityOuter;
};