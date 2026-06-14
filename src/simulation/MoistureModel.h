#pragma once

#include "model/SimulationConfig.h"

// Stage 4 Sprint 4.2: Standalone moisture saturation physics.
//
// Pure stateless functions — no simulation state is modified here.
// All conversions and saturation computations live in this namespace.
// Evaporation, condensation, and latent heat belong to later Sprints.
namespace MoistureModel {

    // Convert a model temperature value to Kelvin.
    // T_K = referenceKelvinTemperature
    //       + modelTemperatureKelvinScale * (T_model - referenceModelTemperature)
    // Result is clamped to [minPhysicalTemperatureK, maxPhysicalTemperatureK].
    double modelTemperatureToKelvin(double temperatureModel, const SimulationConfig& config);

    // Convert a model altitude value to meters.
    // h_m = (altitudeModel / atmosphereHeight) * atmospherePhysicalHeightMeters
    // Result is clamped to >= 0.
    double modelAltitudeToMeters(double altitudeModel, const SimulationConfig& config);

    // Atmospheric pressure [Pa] at a given model altitude.
    // p(h) = seaLevelPressurePa * exp(-h_m / pressureScaleHeightMeters)
    double pressureAtAltitudePa(double altitudeModel, const SimulationConfig& config);

    // Saturation vapor pressure [Pa] at a given temperature in Kelvin.
    // Uses the Magnus/Buck formula:
    //   e_sat = 611.2 * exp(17.67 * (T - 273.15) / (T - 29.65))
    // Returns 0 for non-finite input.
    double saturationVaporPressurePaFromKelvin(double temperatureKelvin);

    // Saturation specific humidity [kg/kg] from temperature [K] and pressure [Pa].
    //   q_sat = 0.622 * e_sat / (p - e_sat)
    // Numerically safe; result clamped to [minSpecificHumidity, maxSpecificHumidity].
    double saturationSpecificHumidityFromKelvinPressure(
        double temperatureKelvin,
        double pressurePa,
        const SimulationConfig& config);

    // Convenience wrapper: model-unit inputs, returns q_sat [kg/kg].
    // Converts temperature and altitude via the config scaling, then calls
    // saturationSpecificHumidityFromKelvinPressure.
    double saturationSpecificHumidity(
        double temperatureModel,
        double altitudeModel,
        const SimulationConfig& config);

    // Diagnostic relative humidity (does not modify any particle state).
    //   RH = specificHumidity / q_sat
    // Returns 0 if q_sat <= 1e-12; result clamped to [0, 5].
    double relativeHumidity(double specificHumidity, double saturationSpecificHumidity);

    // Numerical self-test: computes q_sat at T = 300 K, p = 101325 Pa.
    // Prints result and PASS / WARNING status.
    // Returns true if the result is within the acceptable physical range [0.020, 0.030].
    bool runSaturationSelfTest(const SimulationConfig& config);

} // namespace MoistureModel
