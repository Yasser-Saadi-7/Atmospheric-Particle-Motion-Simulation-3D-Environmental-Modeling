#pragma once
#include "Vec3.h"

struct Parcel {
    int id;         // Unique identifier for the particle
    
    // Kinematic state (Inertial Cartesian coordinates)
    Vec3 r;         // Position
    Vec3 v;         // Velocity
    Vec3 a;         // Acceleration

    // Thermodynamic state
    double T_p;     // Internal temperature
    double mass;    // Particle mass (identical for all)

    // Specific humidity q_p [kg/kg] — Stage 4 moisture model.
    double specificHumidity = 0.0;

    // Default constructor
    Parcel() 
        : id(-1), r(), v(), a(), T_p(0.0), mass(1.0), specificHumidity(0.0) {}

    // Parameterized constructor for easy initialization
    Parcel(int id, const Vec3& position, const Vec3& velocity, double temperature, double mass = 1.0)
        : id(id), r(position), v(velocity), a(), T_p(temperature), mass(mass), specificHumidity(0.0) {}
};