#pragma once

#include <vector>
#include <unordered_map>
#include <cmath>
#include "model/Vec3.h"
#include "model/Parcel.h"
#include "model/SimulationConfig.h"
#include "simulation/Environment.h"

struct CoarseCellIndex {
    int x, y, z;
    
    bool operator==(const CoarseCellIndex& other) const {
        return x == other.x && y == other.y && z == other.z;
    }
};

struct CoarseCellIndexHash {
    std::size_t operator()(const CoarseCellIndex& idx) const {
        std::size_t h1 = std::hash<int>()(idx.x);
        std::size_t h2 = std::hash<int>()(idx.y);
        std::size_t h3 = std::hash<int>()(idx.z);
        return h1 ^ (h2 << 1) ^ (h3 << 2);
    }
};

struct CoarseCellData {
    // ----------------------------------------------------
    // Stage 1: Basic Macroscopic Statistics
    // ----------------------------------------------------
    int particleCount = 0;
    Vec3 meanVelocity = {0.0, 0.0, 0.0};
    double meanKineticTemperature = 0.0;
    
    // ----------------------------------------------------
    // Stage 2: Geometric & Thermal Metadata
    // ----------------------------------------------------
    Vec3 cellCenter = {0.0, 0.0, 0.0};
    double cellRadius = 0.0;
    double altitude = 0.0;
    double latitude = 0.0;           // Stored in radians [-pi/2, pi/2]
    double targetTemperature = 0.0;  // Assigned via Environment model
    
    // ----------------------------------------------------
    // Utilities
    // ----------------------------------------------------
    // Stores IDs of particles in this cell. Crucial for fast variance 
    // calculations and later Stage 2 thermal collisions.
    std::vector<int> particleIndices;
};

class CoarseGrid {
public:
    CoarseGrid(const SimulationConfig& config);

    // Clears and rebuilds the grid, extracting macroscopic stats and evaluating the thermal target
    void build(const std::vector<Parcel>& parcels, const Environment& environment);

    // Geometric helpers
    CoarseCellIndex positionToCell(const Vec3& position) const;
    Vec3 computeCellCenter(const CoarseCellIndex& cell) const;
    
    // Data Accessors
    const CoarseCellData* getCellData(const CoarseCellIndex& cell) const;
    const std::unordered_map<CoarseCellIndex, CoarseCellData, CoarseCellIndexHash>& getAllOccupiedCells() const;

private:
    SimulationConfig config;
    double cellSize;
    std::unordered_map<CoarseCellIndex, CoarseCellData, CoarseCellIndexHash> cells;
};