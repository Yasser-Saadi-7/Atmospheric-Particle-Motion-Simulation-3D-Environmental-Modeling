#include "utils/SphericalUtils.h"
#include <cmath>
#include <algorithm>

// Validation cases (verified analytically):
//
// Case 1 — pure radial motion:
//   pos=(R,0,0)  vel=(1,0,0)
//   e_r=(1,0,0)  e_lat=(0,0,1)  e_lon=(0,1,0)
//   v_r=1  v_theta=0  v_phi_inertial=0
//
// Case 2 — pure eastward motion at equator:
//   pos=(R,0,0)  vel=(0,1,0)
//   v_r=0  v_theta=0  v_phi_inertial=1
//
// Case 3 — pure solid-body rotation:
//   vel = (-Omega*y, Omega*x, 0)
//   v_phi_inertial = Omega*R  (nonzero)
//   v_phi_relative = 0        (rotation-frame residual vanishes)
//   v_r = 0,  v_theta = 0
//
// Case 4 — latitude always in [-90,90] deg; altitude may exceed atmosphereHeight
//           under extreme conditions, but no NaN/inf is produced.

SphericalState computeSphericalState(
    const Vec3& position,
    const Vec3& velocity,
    double planetRadius,
    double angularVelocity)
{
    SphericalState s{};

    double r = position.norm();
    s.radius  = r;
    s.altitude = r - planetRadius;

    if (r < 1e-9) {
        // Particle is at (or arbitrarily close to) the planet center.
        // All angular and directional quantities are undefined — return zeros.
        return s;
    }

    // ---- Radial unit vector ----
    Vec3 e_r = position / r;

    // ---- Latitude and longitude ----
    // Clamp z/r strictly to [-1, 1] before asin to absorb floating-point noise.
    double sin_lat    = std::clamp(position.z / r, -1.0, 1.0);
    s.latitudeRad     = std::asin(sin_lat);
    s.longitudeRad    = std::atan2(position.y, position.x);
    s.latitudeDeg     = s.latitudeRad  * (180.0 / M_PI);
    s.longitudeDeg    = s.longitudeRad * (180.0 / M_PI);

    double cos_lat = std::cos(s.latitudeRad);   // = rho / r, always >= 0
    double cos_lon = std::cos(s.longitudeRad);
    double sin_lon = std::sin(s.longitudeRad);

    // ---- Meridional unit vector (northward, d(e_r)/d(lat), normalised) ----
    // e_lat = (-sin_lat*cos_lon, -sin_lat*sin_lon, cos_lat)
    Vec3 e_lat(-sin_lat * cos_lon,
               -sin_lat * sin_lon,
                cos_lat);

    // ---- Zonal unit vector (eastward) ----
    // e_lon = (-sin_lon, cos_lon, 0)  equivalent to (-y/rho, x/rho, 0)
    // Undefined at the poles (rho -> 0); set zonal components to 0 there.
    double rho = std::sqrt(position.x * position.x + position.y * position.y);
    Vec3 e_lon(0.0, 0.0, 0.0);
    if (rho > 1e-9) {
        e_lon = Vec3(-position.y / rho, position.x / rho, 0.0);
    }

    // ---- Velocity projections in the inertial frame ----
    s.radialVelocity        = velocity.dot(e_r);
    s.meridionalVelocity    = velocity.dot(e_lat);
    s.zonalVelocityInertial = velocity.dot(e_lon);

    // ---- Rotating-frame zonal residual ----
    // Solid-body rotation about z-axis: v_rot = Omega x r = (-Omega*y, Omega*x, 0)
    Vec3 v_rot(-angularVelocity * position.y,
                angularVelocity * position.x,
                0.0);
    Vec3 v_relative          = velocity - v_rot;
    s.zonalVelocityRelative  = v_relative.dot(e_lon);

    return s;
}
