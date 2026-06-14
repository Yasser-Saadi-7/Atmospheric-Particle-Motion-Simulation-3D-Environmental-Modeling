#include "simulation/CoarseGrid.h"

CoarseGrid::CoarseGrid(const SimulationConfig& config) : config(config) {
    // Stage 1 / Stage 2 convention: Coarse cell is 5x the fine interaction cutoff
    cellSize = 5.0 * config.cutoffRadius;
}

CoarseCellIndex CoarseGrid::positionToCell(const Vec3& pos) const {
    return {
        static_cast<int>(std::floor(pos.x / cellSize)),
        static_cast<int>(std::floor(pos.y / cellSize)),
        static_cast<int>(std::floor(pos.z / cellSize))
    };
}

Vec3 CoarseGrid::computeCellCenter(const CoarseCellIndex& cell) const {
    return {
        (cell.x + 0.5) * cellSize,
        (cell.y + 0.5) * cellSize,
        (cell.z + 0.5) * cellSize
    };
}

void CoarseGrid::build(const std::vector<Parcel>& parcels, const Environment& environment) {
    cells.clear();

    // ----------------------------------------------------------------
    // PASS 1: Assign particles to cells and accumulate bulk velocity
    // ----------------------------------------------------------------
    for (size_t i = 0; i < parcels.size(); ++i) {
        CoarseCellIndex idx = positionToCell(parcels[i].r);
        CoarseCellData& data = cells[idx];

        data.particleIndices.push_back(static_cast<int>(i));
        data.particleCount++;
        data.meanVelocity += parcels[i].v;

        // Stage 4 Sprint 4.3: accumulate per-particle specific humidity.
        data.q_sum += parcels[i].specificHumidity;
    }

    // ----------------------------------------------------------------
    // PASS 2: Finalize macroscopic stats & compute Stage 2 targets
    // ----------------------------------------------------------------
    for (auto& pair : cells) {
        const CoarseCellIndex& idx = pair.first;
        CoarseCellData& data = pair.second;

        // 1. Finalize Mean bulk velocity (Wind speed)
        if (data.particleCount > 0) {
            data.meanVelocity = data.meanVelocity / static_cast<double>(data.particleCount);
        }

        // 2. Compute Kinetic Temperature (Variance of velocity)
        double kineticEnergyVariance = 0.0;
        for (int pIdx : data.particleIndices) {
            const Parcel& p = parcels[pIdx];
            Vec3 vDiff = p.v - data.meanVelocity;
            kineticEnergyVariance += p.mass * vDiff.squaredNorm();
        }
        
        if (data.particleCount > 0) {
            data.meanKineticTemperature = kineticEnergyVariance / (3.0 * data.particleCount);
        }

        // 3. Compute Stage 2 Geometric Metadata deterministically
        data.cellCenter = computeCellCenter(idx);
        data.cellRadius = data.cellCenter.norm();
        data.altitude = data.cellRadius - config.planetRadius;
        
        if (data.cellRadius > 1e-9) {
            data.latitude = std::asin(data.cellCenter.z / data.cellRadius);
        } else {
            data.latitude = 0.0;
        }

        // 4. Evaluate Stage 2 Thermal Target using the simplified environment model
        data.targetTemperature = environment.computeTargetTemperatureSimplified(data.cellCenter);

        // 5. Stage 4 Sprint 4.3: compute mean specific humidity q_mean.
        if (data.particleCount > 0) {
            data.q_mean = data.q_sum / static_cast<double>(data.particleCount);
        } else {
            data.q_mean = 0.0;
        }
        if (!std::isfinite(data.q_mean) || data.q_mean < 0.0) {
            data.q_mean = 0.0;
        }
    }
}

const CoarseCellData* CoarseGrid::getCellData(const CoarseCellIndex& cell) const {
    auto it = cells.find(cell);
    if (it != cells.end()) {
        return &(it->second);
    }
    return nullptr;
}

const std::unordered_map<CoarseCellIndex, CoarseCellData, CoarseCellIndexHash>& CoarseGrid::getAllOccupiedCells() const {
    return cells;
}