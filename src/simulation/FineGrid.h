#pragma once

#include <vector>
#include <unordered_map>
#include <array>
#include "model/Vec3.h"
#include "model/Parcel.h"
#include "model/SimulationConfig.h"

// 3D Cartesian cell index
struct CellIndex {
    int x, y, z;
    bool operator==(const CellIndex& other) const {
        return x == other.x && y == other.y && z == other.z;
    }
};

// Hash function for CellIndex
struct CellIndexHash {
    std::size_t operator()(const CellIndex& k) const {
        // Prime multiplication spatial hashing
        return (std::size_t)(k.x * 73856093) ^ 
               (std::size_t)(k.y * 19349663) ^ 
               (std::size_t)(k.z * 83492791);
    }
};

class FineGrid {
public:
    FineGrid() = default;
    FineGrid(const SimulationConfig& config);

    // Clear the current grid
    void clear();

    // Rebuild the grid from the current particle positions
    void build(const std::vector<Parcel>& particles);

    // Convert continuous 3D position to discrete cell index
    CellIndex positionToCell(const Vec3& position) const;

    // Get indices of all particles in a specific cell
    const std::vector<int>& getCellParticles(const CellIndex& cell) const;

    // Get the 27 neighboring cells (including the given cell itself)
    std::array<CellIndex, 27> getNeighborCells(const CellIndex& cell) const;

private:
    double cellSize;
    double invCellSize;
    
    // Maps a 3D cell index to a list of particle indices
    std::unordered_map<CellIndex, std::vector<int>, CellIndexHash> cells;
};