#include "io/OutputWriter.h"
#include "utils/SphericalUtils.h"
#include <iostream>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <filesystem>
#include <cmath>

OutputWriter::OutputWriter(const std::string& outputDir) 
    : outputDir(outputDir), logHeaderWritten(false), zoneHeaderWritten(false),
      sphericalFirstWritten(false), streamfunctionSummaryHeaderWritten(false),
      condensationLogHeaderWritten(false), evaporationLogHeaderWritten(false),
      moistureBalanceLogHeaderWritten(false) {
    if (!std::filesystem::exists(outputDir)) {
        std::filesystem::create_directories(outputDir);
    }
}

std::string OutputWriter::formatStepZeroPadded(int step, int width) const {
    std::ostringstream ss;
    ss << std::setw(width) << std::setfill('0') << step;
    return ss.str();
}

void OutputWriter::writeParticleSnapshot(const std::vector<Parcel>& parcels, int step) const {
    std::string filename = outputDir + "/particles_step_" + formatStepZeroPadded(step) + ".csv";
    std::ofstream file(filename);

    if (!file.is_open()) return;

    // Added radial_velocity for Stage 2 analysis while preserving Stage 1 columns.
    // q_p appended at end for Stage 4 Sprint 4.1 moisture state.
    file << "step,particle_id,x,y,z,vx,vy,vz,temperature,radius,speed,radial_velocity,q_p\n";
    for (const auto& p : parcels) {
        double radius = p.r.norm();
        double radial_velocity = (radius > 1e-9) ? (p.v.dot(p.r) / radius) : 0.0;

        file << step << "," << p.id << ","
             << p.r.x << "," << p.r.y << "," << p.r.z << ","
             << p.v.x << "," << p.v.y << "," << p.v.z << ","
             << p.T_p << "," << radius << "," << p.v.norm() << "," << radial_velocity << ","
             << p.specificHumidity << "\n";
    }
    file.close();
    std::cout << "Particle snapshot written: " << filename << std::endl;
}

void OutputWriter::appendSimulationLog(const std::vector<Parcel>& parcels, int step, 
                                       const Diagnostics::EnergyReport& energy, 
                                       const Diagnostics::ShellBoundsCheck& bounds) {
    std::string filename = outputDir + "/simulation_log.csv";
    std::ofstream file(filename, std::ios::app);

    if (!file.is_open()) return;

    if (!logHeaderWritten) {
        file << "step,particle_count,min_radius,max_radius,outside_bounds,e_kin,e_grav,e_rep,e_total\n";
        logHeaderWritten = true;
    }

    file << step << ","
         << parcels.size() << ","
         << bounds.minRadius << ","
         << bounds.maxRadius << ","
         << bounds.outsideCount << ","
         << energy.kinetic << ","
         << energy.gravitational << ","
         << energy.repulsion << ","
         << energy.total << "\n";

    file.close();
}

void OutputWriter::appendTemperatureZoneLog(int step, double tempEq, double tempMid, double tempPolar) {
    std::string filename = outputDir + "/temperature_zones.csv";
    std::ofstream file(filename, std::ios::app);

    if (!file.is_open()) return;

    if (!zoneHeaderWritten) {
        file << "step,temp_eq_0_30,temp_mid_30_60,temp_polar_60_90\n";
        zoneHeaderWritten = true;
    }

    file << step << "," << tempEq << "," << tempMid << "," << tempPolar << "\n";
    file.close();
}

void OutputWriter::appendCondensationLog(
    int step,
    double condensationThisStep, double cumulativeCondensation,
    double latentHeatingThisStep, double cumulativeLatentHeating,
    long long eventsThisStep, long long cumulativeEvents)
{
    std::string filename = outputDir + "/condensation_log.csv";
    std::ofstream file(filename, std::ios::app);

    if (!file.is_open()) {
        std::cerr << "Error: Could not open condensation log: " << filename << std::endl;
        return;
    }

    if (!condensationLogHeaderWritten) {
        file << "step,"
             << "condensation_this_step,cumulative_condensation,"
             << "latent_heating_this_step,cumulative_latent_heating,"
             << "condensation_events_this_step,cumulative_condensation_events\n";
        condensationLogHeaderWritten = true;
    }

    file << std::fixed << std::setprecision(10)
         << step                    << ","
         << condensationThisStep    << ","
         << cumulativeCondensation  << ","
         << latentHeatingThisStep   << ","
         << cumulativeLatentHeating << ","
         << eventsThisStep          << ","
         << cumulativeEvents        << "\n";

    file.close();
}

void OutputWriter::appendEvaporationLog(
    int step,
    double evaporationThisStep, double cumulativeEvaporation,
    long long eventsThisStep, long long cumulativeEvents)
{
    std::string filename = outputDir + "/evaporation_log.csv";
    std::ofstream file(filename, std::ios::app);

    if (!file.is_open()) {
        std::cerr << "Error: Could not open evaporation log: " << filename << std::endl;
        return;
    }

    if (!evaporationLogHeaderWritten) {
        file << "step,"
             << "evaporation_this_step,cumulative_evaporation,"
             << "evaporation_events_this_step,cumulative_evaporation_events\n";
        evaporationLogHeaderWritten = true;
    }

    file << std::fixed << std::setprecision(10)
         << step                  << ","
         << evaporationThisStep   << ","
         << cumulativeEvaporation << ","
         << eventsThisStep        << ","
         << cumulativeEvents      << "\n";

    file.close();
}

void OutputWriter::appendMoistureBalanceLog(
    int step,
    double totalQ, double initialTotalQ,
    double cumulativeEvaporation, double cumulativeCondensation,
    double expectedTotalQ, double waterBalanceError,
    double waterBalanceRelativeError, const std::string& status)
{
    std::string filename = outputDir + "/moisture_balance.csv";
    std::ofstream file(filename, std::ios::app);

    if (!file.is_open()) {
        std::cerr << "Error: Could not open moisture balance log: " << filename << std::endl;
        return;
    }

    if (!moistureBalanceLogHeaderWritten) {
        file << "step,total_q,initial_total_q,"
             << "cumulative_evaporation,cumulative_condensation,"
             << "expected_total_q,water_balance_error,"
             << "water_balance_relative_error,water_balance_status\n";
        moistureBalanceLogHeaderWritten = true;
    }

    file << std::fixed << std::setprecision(10)
         << step                      << ","
         << totalQ                    << ","
         << initialTotalQ             << ","
         << cumulativeEvaporation     << ","
         << cumulativeCondensation    << ","
         << expectedTotalQ            << ","
         << waterBalanceError         << ","
         << waterBalanceRelativeError << ","
         << status                    << "\n";

    file.close();
}

void OutputWriter::writeCoarseGridSnapshot(const std::unordered_map<CoarseCellIndex, CoarseCellData, CoarseCellIndexHash>& cells, int step) const {
    std::string filename = outputDir + "/coarse_grid_step_" + formatStepZeroPadded(step) + ".csv";
    std::ofstream file(filename);

    if (!file.is_open()) {
        std::cerr << "Error: Could not open coarse grid snapshot for writing: " << filename << std::endl;
        return;
    }

    // q_mean appended at end for Stage 4 Sprint 4.3 moisture statistics.
    file << "step,cell_ix,cell_iy,cell_iz,center_x,center_y,center_z,radius,altitude,latitude,particle_count,mean_vx,mean_vy,mean_vz,mean_kinetic_temperature,target_temperature,q_mean\n";

    for (const auto& pair : cells) {
        const CoarseCellIndex& idx = pair.first;
        const CoarseCellData& data = pair.second;

        // Radial mean velocity (scalar projection of mean wind outward)
        double radial_mean_vel = 0.0;
        if (data.cellRadius > 1e-9) {
            radial_mean_vel = data.meanVelocity.dot(data.cellCenter) / data.cellRadius;
        }

        file << step << ","
             << idx.x << "," << idx.y << "," << idx.z << ","
             << data.cellCenter.x << "," << data.cellCenter.y << "," << data.cellCenter.z << ","
             << data.cellRadius << ","
             << data.altitude << ","
             << data.latitude << ","
             << data.particleCount << ","
             << data.meanVelocity.x << "," << data.meanVelocity.y << "," << data.meanVelocity.z << ","
             << data.meanKineticTemperature << ","
             << data.targetTemperature << ","
             << data.q_mean << "\n";
    }

    file.close();
    std::cout << "Coarse grid snapshot written: " << filename << std::endl;

    // Stage 4 Sprint 4.3: coarse humidity diagnostics.
    {
        double q_min  =  1e30;
        double q_max  = -1e30;
        double q_sum  =  0.0;
        int    count  =  0;
        for (const auto& pair : cells) {
            const CoarseCellData& d = pair.second;
            if (d.particleCount > 0) {
                q_min  = std::min(q_min, d.q_mean);
                q_max  = std::max(q_max, d.q_mean);
                q_sum += d.q_mean;
                ++count;
            }
        }
        if (count > 0) {
            std::cout << "  Coarse humidity stats at step " << step
                      << ": min_q_mean=" << q_min
                      << ", max_q_mean=" << q_max
                      << ", mean_q_mean=" << (q_sum / count) << std::endl;
        }
    }
}

void OutputWriter::writeParticleSphericalDiagnostics(
    const std::vector<Parcel>& parcels,
    int step,
    double planetRadius,
    double angularVelocity)
{
    std::string filename = outputDir + "/particle_spherical_step_" + formatStepZeroPadded(step) + ".csv";
    std::ofstream file(filename);

    if (!file.is_open()) {
        std::cerr << "Error: Could not open spherical diagnostics file: " << filename << std::endl;
        return;
    }

    // q_p appended at end for Stage 4 Sprint 4.1 moisture state.
    file << "step,particle_id,x,y,z,vx,vy,vz,"
         << "radius,altitude,latitude_deg,longitude_deg,"
         << "v_r,v_theta,v_phi_inertial,v_phi_relative,temperature,q_p\n";

    // Capture first valid particle for the one-time summary log
    bool sampleCaptured = false;
    double sampleLat = 0.0, sampleAlt = 0.0, sampleVr = 0.0,
           sampleVtheta = 0.0, sampleVphiRel = 0.0;

    for (const auto& p : parcels) {
        SphericalState s = computeSphericalState(p.r, p.v, planetRadius, angularVelocity);

        // Guard against any residual NaN / inf before writing
        if (!std::isfinite(s.radius)         || !std::isfinite(s.altitude)      ||
            !std::isfinite(s.latitudeDeg)    || !std::isfinite(s.longitudeDeg)  ||
            !std::isfinite(s.radialVelocity) || !std::isfinite(s.meridionalVelocity) ||
            !std::isfinite(s.zonalVelocityInertial) || !std::isfinite(s.zonalVelocityRelative)) {
            std::cerr << "[WARNING] Non-finite spherical state for particle " << p.id
                      << " at step " << step << " — row skipped.\n";
            continue;
        }

        file << step      << ","
             << p.id      << ","
             << p.r.x     << "," << p.r.y     << "," << p.r.z     << ","
             << p.v.x     << "," << p.v.y     << "," << p.v.z     << ","
             << s.radius  << "," << s.altitude << ","
             << s.latitudeDeg  << "," << s.longitudeDeg  << ","
             << s.radialVelocity       << ","
             << s.meridionalVelocity   << ","
             << s.zonalVelocityInertial << ","
             << s.zonalVelocityRelative << ","
             << p.T_p << ","
             << p.specificHumidity << "\n";

        if (!sampleCaptured) {
            sampleLat      = s.latitudeDeg;
            sampleAlt      = s.altitude;
            sampleVr       = s.radialVelocity;
            sampleVtheta   = s.meridionalVelocity;
            sampleVphiRel  = s.zonalVelocityRelative;
            sampleCaptured = true;
        }
    }

    file.close();
    std::cout << "Particle spherical diagnostics written: " << filename << std::endl;

    // Print one-time summary on the first Stage 3 write
    if (!sphericalFirstWritten && sampleCaptured) {
        sphericalFirstWritten = true;
        std::cout << "  [Stage 3 First Diagnostics — Sample Particle]" << std::endl;
        std::cout << "    latitude:    " << sampleLat      << " deg" << std::endl;
        std::cout << "    altitude:    " << sampleAlt      << std::endl;
        std::cout << "    v_r:         " << sampleVr       << std::endl;
        std::cout << "    v_theta:     " << sampleVtheta   << std::endl;
        std::cout << "    v_phi_rel:   " << sampleVphiRel  << std::endl;
    }
}

void OutputWriter::writeCirculationAverages(
    int step,
    const std::vector<CirculationCellAverages>& averages)
{
    std::string filename = outputDir + "/circulation_accum_step_" + formatStepZeroPadded(step) + ".csv";
    std::ofstream file(filename);

    if (!file.is_open()) {
        std::cerr << "Error: Could not open circulation averages file: " << filename << std::endl;
        return;
    }

    file << "step,latitude_bin,altitude_bin,latitude_center_deg,altitude_center,"
         << "samples,mean_particle_count,mean_density_proxy,"
         << "mean_v_theta,std_v_theta,mean_mass_flux\n";

    int    binsWritten    = 0;
    double maxAbsVTheta   = 0.0;
    double maxAbsMassFlux = 0.0;

    for (const auto& cell : averages) {
        if (cell.samples == 0) continue;

        // Guard against any residual NaN / inf before writing
        if (!std::isfinite(cell.meanVTheta)      || !std::isfinite(cell.meanMassFlux)    ||
            !std::isfinite(cell.meanParticleCount)|| !std::isfinite(cell.stdVTheta)       ||
            !std::isfinite(cell.latitudeCenterDeg)|| !std::isfinite(cell.altitudeCenter)) {
            std::cerr << "[WARNING] Non-finite circulation average at lat_bin=" << cell.latIndex
                      << " alt_bin=" << cell.altIndex << " — row skipped.\n";
            continue;
        }

        file << std::fixed << std::setprecision(6)
             << step                   << ","
             << cell.latIndex          << ","
             << cell.altIndex          << ","
             << cell.latitudeCenterDeg << ","
             << cell.altitudeCenter    << ","
             << cell.samples           << ","
             << cell.meanParticleCount << ","
             << cell.meanDensityProxy  << ","
             << cell.meanVTheta        << ","
             << cell.stdVTheta         << ","
             << cell.meanMassFlux      << "\n";

        ++binsWritten;
        maxAbsVTheta   = std::max(maxAbsVTheta,   std::abs(cell.meanVTheta));
        maxAbsMassFlux = std::max(maxAbsMassFlux, std::abs(cell.meanMassFlux));
    }

    file.close();
    std::cout << "Circulation accumulation written: " << filename << std::endl;
    std::cout << "  Bins with samples:    " << binsWritten    << std::endl;
    std::cout << "  Max |mean_v_theta|:   " << maxAbsVTheta   << std::endl;
    std::cout << "  Max |mean_mass_flux|: " << maxAbsMassFlux << std::endl;
}

void OutputWriter::writeStreamfunction(
    int step,
    const std::vector<StreamfunctionCell>&  cells,
    const StreamfunctionSummary&            summary)
{
    // ---- Per-step Psi grid file ----
    std::string gridFile = outputDir + "/streamfunction_step_" + formatStepZeroPadded(step) + ".csv";
    {
        std::ofstream file(gridFile);
        if (!file.is_open()) {
            std::cerr << "Error: Could not open streamfunction file: " << gridFile << std::endl;
            return;
        }

        file << "step,latitude_bin,altitude_bin,latitude_center_deg,altitude_center,"
             << "samples,mean_v_theta,mean_mass_flux,psi\n";

        for (const auto& sc : cells) {
            // Guard against any residual NaN / inf before writing
            if (!std::isfinite(sc.psi)               ||
                !std::isfinite(sc.meanVTheta)         ||
                !std::isfinite(sc.meanMassFlux)       ||
                !std::isfinite(sc.latitudeCenterDeg)  ||
                !std::isfinite(sc.altitudeCenter)) {
                std::cerr << "[WARNING] Non-finite streamfunction cell at lat_bin="
                          << sc.latitudeBin << " alt_bin=" << sc.altitudeBin
                          << " — row skipped.\n";
                continue;
            }

            file << std::fixed << std::setprecision(6)
                 << step                  << ","
                 << sc.latitudeBin        << ","
                 << sc.altitudeBin        << ","
                 << sc.latitudeCenterDeg  << ","
                 << sc.altitudeCenter     << ","
                 << sc.samples            << ","
                 << sc.meanVTheta         << ","
                 << sc.meanMassFlux       << ","
                 << sc.psi                << "\n";
        }
        file.close();
    }

    // ---- Append one row to the running summary file ----
    std::string summaryFile = outputDir + "/streamfunction_summary.csv";
    {
        std::ofstream file(summaryFile, std::ios::app);
        if (!file.is_open()) {
            std::cerr << "Error: Could not open streamfunction summary: " << summaryFile << std::endl;
            return;
        }

        if (!streamfunctionSummaryHeaderWritten) {
            file << "step,max_abs_psi,min_psi,max_psi,cells_with_samples\n";
            streamfunctionSummaryHeaderWritten = true;
        }

        file << std::fixed << std::setprecision(6)
             << step               << ","
             << summary.maxAbsPsi  << ","
             << summary.minPsi     << ","
             << summary.maxPsi     << ","
             << summary.cellsWithSamples << "\n";
        file.close();
    }

    std::cout << "Streamfunction written: " << gridFile << std::endl;
    std::cout << "Streamfunction summary updated: " << summaryFile << std::endl;
    std::cout << "  Max |Psi|:          " << summary.maxAbsPsi        << std::endl;
    std::cout << "  Cells with samples: " << summary.cellsWithSamples << std::endl;
}