#pragma once

#include "model/Vec3.h"

// All velocity magnitudes are in model units.
// Latitude and longitude are stored in both radians and degrees for convenience.
struct SphericalState {
    double radius;                  // r: distance from planet center
    double altitude;                // h = r - planetRadius

    double latitudeRad;             // phi in [-pi/2, pi/2]
    double longitudeRad;            // lambda in [-pi, pi]
    double latitudeDeg;             // latitude in degrees [-90, 90]
    double longitudeDeg;            // longitude in degrees [-180, 180]

    double radialVelocity;          // v_r:  outward radial component
    double meridionalVelocity;      // v_theta: northward meridional component
    double zonalVelocityInertial;   // v_phi: eastward zonal in inertial frame
    double zonalVelocityRelative;   // v_phi: eastward zonal relative to rotating planet
};

// Decompose a particle's Cartesian position and inertial velocity into spherical
// atmospheric coordinates plus the rotating-frame zonal residual.
//
// Unit vector definitions (all orthonormal):
//   e_r     = r / |r|                                   (radially outward)
//   e_lat   = (-sin_lat*cos_lon, -sin_lat*sin_lon, cos_lat)   (northward)
//   e_lon   = (-sin_lon, cos_lon, 0)                   (eastward / zonal)
//
// Rotating-frame zonal velocity:
//   v_rot        = Omega x r = (-Omega*y, Omega*x, 0)
//   v_relative   = velocity - v_rot
//   v_phi_rel    = v_relative . e_lon
//
// Numerical safety:
//   - Returns all-zero state if |r| < 1e-9 (particle at origin).
//   - Clamps z/r to [-1,1] before asin to guard floating-point noise.
//   - Sets zonal components to 0 when rho < 1e-9 (at poles).
SphericalState computeSphericalState(
    const Vec3& position,
    const Vec3& velocity,
    double planetRadius,
    double angularVelocity
);
