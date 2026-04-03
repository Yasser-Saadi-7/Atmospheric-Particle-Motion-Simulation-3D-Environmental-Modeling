#ifndef PARCEL_H
#define PARCEL_H

#include "Vec3.h"

struct Parcel {
    Vec3 position;
    Vec3 velocity;
    Vec3 acceleration;

    double mass;
    double temperature;
    double pressure;
    double density;
    double humidity;

    Parcel()
        : position(), velocity(), acceleration(),
          mass(1.0), temperature(300.0),
          pressure(101325.0), density(1.225), humidity(0.0) {}
};

#endif