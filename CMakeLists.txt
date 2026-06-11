cmake_minimum_required(VERSION 3.10)
project(AtmosphericSimulation)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenMP)

include_directories(src)

add_executable(AtmosphericSimulation
    src/main.cpp
    src/simulation/SimulationEngine.cpp
    src/simulation/Environment.cpp
    src/simulation/ThermalModel.cpp
    src/simulation/FineGrid.cpp
    src/simulation/CoarseGrid.cpp
    src/simulation/BoundaryHandler.cpp
    src/simulation/Integrator.cpp
    src/io/OutputWriter.cpp
    src/analysis/Diagnostics.cpp
    src/analysis/CirculationAccumulator.cpp
    src/utils/SphericalUtils.cpp
)

if(OpenMP_CXX_FOUND)
    target_link_libraries(AtmosphericSimulation PUBLIC OpenMP::OpenMP_CXX)
endif()