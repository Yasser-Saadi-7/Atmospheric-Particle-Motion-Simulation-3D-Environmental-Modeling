#include "simulation/MoistureModel.h"
#include <cmath>
#include <algorithm>
#include <iostream>

namespace MoistureModel {

// ---------------------------------------------------------------------------
// Temperature conversion
// ---------------------------------------------------------------------------

double modelTemperatureToKelvin(double temperatureModel, const SimulationConfig& config) {
    double T_K = config.referenceKelvinTemperature
               + config.modelTemperatureKelvinScale
                 * (temperatureModel - config.referenceModelTemperature);

    return std::clamp(T_K, config.minPhysicalTemperatureK, config.maxPhysicalTemperatureK);
}

// ---------------------------------------------------------------------------
// Altitude conversion
// ---------------------------------------------------------------------------

double modelAltitudeToMeters(double altitudeModel, const SimulationConfig& config) {
    if (config.atmosphereHeight <= 0.0) {
        // Safe fallback: treat model altitude as a fraction of the physical height.
        return std::max(0.0, altitudeModel * config.atmospherePhysicalHeightMeters);
    }
    double h_m = (altitudeModel / config.atmosphereHeight)
               * config.atmospherePhysicalHeightMeters;
    return std::max(0.0, h_m);
}

// ---------------------------------------------------------------------------
// Pressure profile
// ---------------------------------------------------------------------------

double pressureAtAltitudePa(double altitudeModel, const SimulationConfig& config) {
    double h_m = modelAltitudeToMeters(altitudeModel, config);
    double p   = config.seaLevelPressurePa
               * std::exp(-h_m / config.pressureScaleHeightMeters);

    // Guard against underflow to zero; maintain a tiny positive floor.
    return std::max(p, 1.0);
}

// ---------------------------------------------------------------------------
// Saturation vapor pressure — Magnus/Buck formula
// ---------------------------------------------------------------------------

double saturationVaporPressurePaFromKelvin(double T) {
    if (!std::isfinite(T)) return 0.0;

    double denom = T - 29.65;
    // Avoid denominator collapse (physically T < 30 K never occurs in the atmosphere).
    if (std::abs(denom) < 1e-6) return 0.0;

    double exponent = 17.67 * (T - 273.15) / denom;
    double e_sat    = 611.2 * std::exp(exponent);

    return (std::isfinite(e_sat) && e_sat >= 0.0) ? e_sat : 0.0;
}

// ---------------------------------------------------------------------------
// Saturation specific humidity
// ---------------------------------------------------------------------------

double saturationSpecificHumidityFromKelvinPressure(
    double temperatureKelvin,
    double pressurePa,
    const SimulationConfig& config)
{
    if (pressurePa <= 0.0) return config.minSpecificHumidity;

    double e_sat = saturationVaporPressurePaFromKelvin(temperatureKelvin);

    // If e_sat exceeds total pressure the formula breaks down — clamp it.
    if (e_sat >= pressurePa) e_sat = 0.99 * pressurePa;

    double denom = pressurePa - e_sat;
    if (denom <= 0.0) return config.minSpecificHumidity;

    double q_sat = 0.622 * e_sat / denom;

    if (!std::isfinite(q_sat)) return config.minSpecificHumidity;

    return std::clamp(q_sat, config.minSpecificHumidity, config.maxSpecificHumidity);
}

// ---------------------------------------------------------------------------
// Model-unit convenience wrapper
// ---------------------------------------------------------------------------

double saturationSpecificHumidity(
    double temperatureModel,
    double altitudeModel,
    const SimulationConfig& config)
{
    double T_K = modelTemperatureToKelvin(temperatureModel, config);
    double p   = pressureAtAltitudePa(altitudeModel, config);
    return saturationSpecificHumidityFromKelvinPressure(T_K, p, config);
}

// ---------------------------------------------------------------------------
// Relative humidity (diagnostic only)
// ---------------------------------------------------------------------------

double relativeHumidity(double specificHumidity, double saturationSpecificHumidity) {
    if (saturationSpecificHumidity <= 1e-12) return 0.0;
    double rh = specificHumidity / saturationSpecificHumidity;
    return std::clamp(rh, 0.0, 5.0);
}

// ---------------------------------------------------------------------------
// Numerical self-test
// ---------------------------------------------------------------------------

bool runSaturationSelfTest(const SimulationConfig& config) {
    constexpr double TEST_T_K = 300.0;
    constexpr double TEST_P   = 101325.0;

    double q_sat = saturationSpecificHumidityFromKelvinPressure(TEST_T_K, TEST_P, config);

    constexpr double ACCEPTABLE_MIN = 0.020;
    constexpr double ACCEPTABLE_MAX = 0.030;
    bool pass = std::isfinite(q_sat) && q_sat >= ACCEPTABLE_MIN && q_sat <= ACCEPTABLE_MAX;

    std::cout << "--- Stage 4 Sprint 4.2 saturation self-test ---" << std::endl;
    std::cout << "  q_sat(T=300 K, p=101325 Pa) = " << q_sat << " kg/kg" << std::endl;
    std::cout << "  Expected approximately 0.022-0.023 kg/kg "
                 "(acceptable range 0.020 – 0.030)" << std::endl;
    std::cout << "  Status: " << (pass ? "PASS" : "WARNING — value outside expected range")
              << std::endl;

    return pass;
}

} // namespace MoistureModel
