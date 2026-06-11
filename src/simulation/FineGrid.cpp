#include "simulation/FineGrid.h"
#include <cmath>

FineGrid::FineGrid(const SimulationConfig& config) {
    cellSize = config.cutoffRadius;
    invCellSize = (cellSize > 0.0) ? 1.0 / cellSize : 1.0;
}

void FineGrid::clear() {
    cells.clear();
}

void FineGrid::build(const std::vector<Parcel>& particles) {
    clear();
    for (size_t i = 0; i < particles.size(); ++i) {
        CellIndex cell = positionToCell(particles[i].r);
        cells[cell].push_back(static_cast<int>(i));
    }
}

CellIndex FineGrid::positionToCell(const Vec3& position) const {
    // Floor is critical to handle negative coordinates consistently
    return CellIndex{
        static_cast<int>(std::floor(position.x * invCellSize)),
        static_cast<int>(std::floor(position.y * invCellSize)),
        static_cast<int>(std::floor(position.z * invCellSize))
    };
}

const std::vector<int>& FineGrid::getCellParticles(const CellIndex& cell) const {
    // Return empty vector if the cell is completely empty (not in the map)
    static const std::vector<int> emptyVec;
    auto it = cells.find(cell);
    if (it != cells.end()) {
        return it->second;
    }
    return emptyVec;
}

std::array<CellIndex, 27> FineGrid::getNeighborCells(const CellIndex& cell) const {
    std::array<CellIndex, 27> neighbors;
    int idx = 0;
    
    // Generate the 3x3x3 block of surrounding cells
    for (int dx = -1; dx <= 1; ++dx) {
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dz = -1; dz <= 1; ++dz) {
                neighbors[idx++] = CellIndex{cell.x + dx, cell.y + dy, cell.z + dz};
            }
        }
    }
    
    return neighbors;
}