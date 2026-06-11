#include "simulation/Integrator.h"
#include "simulation/ForceModel.h"

Integrator::Integrator(const SimulationConfig& config) 
    : config(config), boundaryHandler(config) {}

void Integrator::initialize(std::vector<Parcel>& parcels, const FineGrid& fineGrid) {
    computeForces(parcels, fineGrid);
}

void Integrator::step(std::vector<Parcel>& parcels, FineGrid& fineGrid) {
    double dt = config.dt;
    double half_dt = 0.5 * dt;

    // 1. First half-step velocity update & full position update
    for (auto& p : parcels) {
        p.v += p.a * half_dt;
        p.r += p.v * dt;
    }

    // 2. Apply purely radial boundary conditions immediately after position change
    boundaryHandler.applyAll(parcels);

    // 3. Rebuild spatial structures based on bounded r(t + dt)
    fineGrid.build(parcels);

    // 4. Compute new forces / accelerations a(t + dt)
    computeForces(parcels, fineGrid);

    // 5. Second half-step velocity update
    for (auto& p : parcels) {
        p.v += p.a * half_dt;
    }
}

void Integrator::computeForces(std::vector<Parcel>& parcels, const FineGrid& fineGrid) {
    for (auto& p : parcels) {
        Vec3 totalForce(0.0, 0.0, 0.0);

        // Stage 1 Physics: Gravity
        totalForce += ForceModel::computeGravity(p, config);

        // Stage 1 Physics: Phase 1 Damping
        totalForce += ForceModel::computeDamping(p, config);

        // Stage 1 Physics: Soft-sphere Repulsion
        CellIndex cell = fineGrid.positionToCell(p.r);
        std::array<CellIndex, 27> neighbors = fineGrid.getNeighborCells(cell);

        for (const auto& neighborCell : neighbors) {
            const auto& cellParticles = fineGrid.getCellParticles(neighborCell);
            for (int j_idx : cellParticles) {
                if (p.id != parcels[j_idx].id) {
                    totalForce += ForceModel::computePairRepulsion(p, parcels[j_idx], config);
                }
            }
        }

        // Convert accumulated force to acceleration (a = F/m)
        p.a = totalForce / p.mass;
    }
}

void Integrator::setDamping(double newGamma) {
    this->config.dampingGamma = newGamma;
    
    
}