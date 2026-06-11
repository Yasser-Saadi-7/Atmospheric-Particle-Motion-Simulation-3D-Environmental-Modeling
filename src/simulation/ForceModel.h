#pragma once

#include <cmath>
#include "model/Vec3.h"
#include "model/Parcel.h"
#include "model/SimulationConfig.h"

namespace ForceModel {

    /**
     * Computes radial gravity force directed towards the origin.
     * F_grav = -m * g * r_hat
     */
    inline Vec3 computeGravity(const Parcel& p, const SimulationConfig& config) {
        double r_norm = p.r.norm();
        if (r_norm > 0.0) {
            // Direction towards origin is -p.r / r_norm
            return p.r * (-p.mass * config.gravity / r_norm);
        }
        return Vec3(0.0, 0.0, 0.0);
    }

    /**
     * Computes soft-sphere pairwise repulsion between particle i and particle j.
     * F(r) = k * (sigma^2 - r^2) * r_hat_ij    for r < sigma
     * Force is limited by config.maxForce to prevent numerical blow-ups.
     */
    inline Vec3 computePairRepulsion(const Parcel& p_i, const Parcel& p_j, const SimulationConfig& config) {
        Vec3 r_vec = p_i.r - p_j.r; // Vector pointing from j to i
        double r_sq = r_vec.squaredNorm();
        double sigma_sq = config.sigma * config.sigma;

        if (r_sq > 0.0 && r_sq < sigma_sq) {
            double r_dist = std::sqrt(r_sq);
            double mag = config.repulsionStiffness * (sigma_sq - r_sq);
            
            // Apply force limiter
            if (mag > config.maxForce) {
                mag = config.maxForce;
            }
            
            // F = magnitude * unit_vector
            return r_vec * (mag / r_dist);
        }
        
        return Vec3(0.0, 0.0, 0.0);
    }

    /**
     * Computes damping force. strictly for Phase 1 to drive hydrostatic equilibrium.
     * F_damp = -gamma * m * (v - v_rot(position))
     * where v_rot = Omega x position = (-Omega * y, Omega * x, 0)
     */
    inline Vec3 computeDamping(const Parcel& p, const SimulationConfig& config) {
        // Compute local target velocity due to planetary rotation
        Vec3 v_rot(-config.angularVelocity * p.r.y, 
                    config.angularVelocity * p.r.x, 
                    0.0);
        
        Vec3 diff = p.v - v_rot;
        return diff * (-config.dampingGamma * p.mass);
    }

} // namespace ForceModel