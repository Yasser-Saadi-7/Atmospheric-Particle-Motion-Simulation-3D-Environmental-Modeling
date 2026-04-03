cmake_minimum_required(VERSION 3.10)

project(AtmosphericSimulation)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(AtmosphericSimulation
    src/main.cpp
    src/simulation/SimulationEngine.cpp
)

target_include_directories(AtmosphericSimulation PRIVATE src)