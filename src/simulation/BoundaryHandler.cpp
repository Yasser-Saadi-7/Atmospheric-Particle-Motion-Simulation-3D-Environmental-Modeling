#include "simulation/BoundaryHandler.h"

BoundaryHandler::BoundaryHandler(const SimulationConfig& config) {
    rInner = config.planetRadius;
    rOuter = config.planetRadius + config.atmosphereHeight;
    elasticityInner = config.elasticityInner;
    elasticityOuter = config.elasticityOuter;
}

void BoundaryHandler::apply(Parcel& p) const {
    double r_norm = p.r.norm();

    // Safe fallback for the singularity at the exact origin
    if (r_norm == 0.0) {
        p.r = Vec3(0.0, 0.0, rInner); // Push to north pole of inner boundary
        r_norm = rInner;
    }

    if (r_norm < rInner) {
        // Compute radial unit vector
        Vec3 r_hat = p.r / r_norm;
        
        // Project position back to the inner sphere
        p.r = r_hat * rInner;

        // Decompose velocity into radial magnitude
        double v_rad_mag = p.v.dot(r_hat);
        
        // Only reflect if the particle is moving inward
        if (v_rad_mag < 0.0) {
            Vec3 v_rad = r_hat * v_rad_mag;
            Vec3 v_tan = p.v - v_rad;
            
            // Reflect only the radial component
            Vec3 v_rad_new = v_rad * (-elasticityInner);
            
            // Reconstruct velocity
            p.v = v_tan + v_rad_new;
        }
    } 
    else if (r_norm > rOuter) {
        // Compute radial unit vector
        Vec3 r_hat = p.r / r_norm;
        
        // Project position back to the outer sphere
        p.r = r_hat * rOuter;

        // Decompose velocity into radial magnitude
        double v_rad_mag = p.v.dot(r_hat);
        
        // Only reflect if the particle is moving outward
        if (v_rad_mag > 0.0) {
            Vec3 v_rad = r_hat * v_rad_mag;
            Vec3 v_tan = p.v - v_rad;
            
            // Reflect only the radial component
            Vec3 v_rad_new = v_rad * (-elasticityOuter);
            
            // Reconstruct velocity
            p.v = v_tan + v_rad_new;
        }
    }
}

void BoundaryHandler::applyAll(std::vector<Parcel>& parcels) const {
    for (auto& p : parcels) {
        apply(p);
    }
}