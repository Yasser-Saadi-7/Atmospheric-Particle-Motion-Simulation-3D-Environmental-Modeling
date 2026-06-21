# Physics Model Report — AtmosphericSimulation

*Prepared by: code inspection of all source files in `src/`.*
*Date: 2026-06-14*
*Project authors: Yasser Sadi, Diana Hujerat. Advisor: Dr. Zakharia Frenkel.*

---

## 1. Overview

AtmosphericSimulation is a three-dimensional, particle-based model of a planetary atmosphere. It is best described as a **Lagrangian molecular-dynamics-inspired** simulation in which the atmosphere is represented by a large ensemble of macroscopic air parcels that move through, and interact within, a spherical shell surrounding a model planet.

The goal is to qualitatively reproduce several important atmospheric mechanisms — hydrostatic density stratification, meridional thermal gradients, convective overturning, planetary rotation effects, and a simplified water-vapor cycle — without solving the full continuum fluid equations. The model is therefore a simplified research and educational tool, not a numerical weather-prediction or general circulation model (GCM).

All physical quantities in the simulation use **internal model units** that are not directly calibrated to Earth's SI system, except where explicitly scaled (as in the moisture physics module). Comparisons with real atmospheric values should therefore be treated as qualitative indicators only.

---

## 2. Atmospheric Representation

### 2.1 Why particles?

Real atmospheric fluid parcels obey the Navier–Stokes equations, which require discretizing a continuous velocity and pressure field. Here, the continuum is replaced by a set of **N = 10,000 discrete parcels**, each representing a macroscopic lump of air. This Lagrangian approach makes it straightforward to track individual parcel trajectories, apply stochastic thermal forcing, and add moisture as a per-parcel scalar without solving a pressure Poisson equation.

### 2.2 Parcel state variables

Each parcel is described by a `Parcel` struct (defined in `src/model/Parcel.h`):

| Variable | Symbol | Type | Meaning |
|---|---|---|---|
| `r` | **r** | `Vec3` | 3D Cartesian position (model units) |
| `v` | **v** | `Vec3` | 3D Cartesian velocity (model units/step) |
| `a` | **a** | `Vec3` | 3D acceleration from the current force evaluation |
| `T_p` | T_p | `double` | Parcel temperature (model units, derived from velocity variance) |
| `mass` | m | `double` | Parcel mass (fixed at 1.0 for all parcels) |
| `specificHumidity` | q_p | `double` | Specific humidity carried by the parcel (kg/kg scale) |

`T_p` is defined kinetically as the squared thermal speed divided by three:

\[
T_p = \frac{|\mathbf{v}_{\rm th}|^2}{3}
\]

where **v**_th = **v** − **v**_mean is the velocity relative to the local mean flow of the coarse cell. This is a model-unit analogue of kinetic temperature.

### 2.3 Spherical shell geometry

The valid domain is the spherical shell:

\[
R \le |\mathbf{r}| \le R + H
\]

with parameters from `src/model/SimulationConfig.h`:

| Parameter | Symbol | Value | Meaning |
|---|---|---|---|
| `planetRadius` | R | 50.0 | Planet surface radius (model units) |
| `atmosphereHeight` | H | 20.0 | Atmosphere thickness (model units) |

The ratio H/R = 0.4 is large by Earth standards (Earth's H/R ≈ 0.015), making this a thick-shell model. Latitude is computed as:

\[
\theta = \arcsin\!\left(\frac{z}{r}\right), \quad r = |\mathbf{r}|
\]

and altitude as h = r − R. Both are implemented in `src/simulation/Environment.cpp` and `src/utils/SphericalUtils.cpp`.

---

## 3. Forces

All forces are accumulated in `src/simulation/Integrator.cpp` (`computeForces`) and computed by helper functions in `src/simulation/ForceModel.h` (header-only). Three force contributions exist: gravity, soft-sphere repulsion, and a damping force. The damping force is always called by the integrator but its coefficient is set to zero after Phase 1 (see Section 3.3).

### 3.1 Soft-sphere repulsion

**Formula** (from `ForceModel::computePairRepulsion`, `src/simulation/ForceModel.h`):

\[
\mathbf{F}_{ij} = k\,(\sigma^2 - r_{ij}^2)\,\hat{\mathbf{r}}_{ij}, \quad r_{ij} < \sigma
\]

where:
- \(r_{ij} = |\mathbf{r}_i - \mathbf{r}_j|\) is the inter-parcel distance,
- \(\hat{\mathbf{r}}_{ij} = (\mathbf{r}_i - \mathbf{r}_j)/r_{ij}\) points from j toward i,
- k = `repulsionStiffness` = 200.0,
- σ = `sigma` = 2.0 (also the cutoff radius for neighbor search).

The force magnitude is **capped** at `maxForce` = 100.0 to prevent numerical blow-ups at very short separations:

```cpp
if (mag > config.maxForce) mag = config.maxForce;
```

**Purpose:** This harmonic-well repulsion prevents parcels from overlapping, effectively mimicking the excluded-volume (pressure) effect that keeps air parcels separated. It is a simplified substitute for a true equation of state.

**Limitations:**
- The force shape (σ² − r²) is not derived from thermodynamic first principles. It differs from both Lennard-Jones and hard-sphere potentials.
- It has no attractive tail; parcels interact only repulsively.
- The cutoff σ = 2.0 means only immediately neighboring parcels interact. Long-range pressure waves (sound) are not propagated correctly.
- The force limiter introduces an artificial floor on minimum inter-parcel distance that is not physically calibrated.

### 3.2 Gravity

**Formula** (from `ForceModel::computeGravity`, `src/simulation/ForceModel.h`):

\[
\mathbf{F}_{\rm grav} = -m\,g\,\hat{\mathbf{r}} = -m\,g\,\frac{\mathbf{r}}{|\mathbf{r}|}
\]

with g = `gravity` = 0.016 (model units). The force points radially inward toward the planetary center for all r > 0.

**Role:** Gravity pulls parcels toward the surface. In equilibrium, upward soft-sphere repulsion from denser lower layers balances gravity, creating a **hydrostatic density stratification** in which parcel number density decreases with altitude. This is the qualitative analogue of the real hydrostatic balance.

**Limitations:**
- The gravity magnitude is constant and does not decrease with altitude (i.e., no 1/r² falloff). This is the flat-space approximation g ≈ const, which is reasonable only for shallow atmospheres. In this thick-shell model it introduces some inaccuracy at high altitude.
- There is no explicit pressure variable. The hydrostatic balance is emergent from the repulsion–gravity interplay, not enforced analytically.
- `src/utils/Constants.h` defines a constant `GRAVITY = 9.81`, but this value is **not used** anywhere in the simulation. The operative value is always `config.gravity = 0.016`.

### 3.3 Damping

**Formula** (from `ForceModel::computeDamping`, `src/simulation/ForceModel.h`):

\[
\mathbf{F}_{\rm damp} = -\gamma\,m\,(\mathbf{v} - \mathbf{v}_{\rm rot})
\]

where:

\[
\mathbf{v}_{\rm rot} = \boldsymbol{\Omega} \times \mathbf{r} = (-\Omega\,y,\ \Omega\,x,\ 0)
\]

is the local co-rotation velocity, with Ω = `angularVelocity` = 0.01, and γ = `dampingGamma` = 100.0 during Phase 1.

**Phase control:** The damping coefficient is set to γ = 100.0 during Phase 1 (steps 1–20,000). At the start of Phase 2, `runPhase2()` in `SimulationEngine.cpp` calls:

```cpp
config.dampingGamma = 0.0;
integrator.setDamping(0.0);
```

making F_damp = **0** for all subsequent phases. The `computeDamping` function is still invoked every step by the integrator, but it returns the zero vector when γ = 0.

**Purpose of Phase 1 damping:** The parcels are initialized with random positions and small random velocities. Without damping, inter-parcel repulsion and gravity would drive violent transients that prevent the system from settling into a stable stratified shell. The large damping force (γ = 100) rapidly dissipates kinetic energy and steers each parcel toward the rigid co-rotation velocity, allowing the shell to form a quasi-hydrostatic density profile within 20,000 steps.

**Why damping must be disabled afterward:** If γ remained active during Phases 2 and 3, it would continuously extract kinetic energy from any thermal or rotational motion, suppressing convection, circulation, and all dynamical phenomena of interest. Physical atmospheres have no such large-scale frictional damping; real dissipation occurs at the molecular level and is represented here by the stochastic thermal model instead.

---

## 4. Boundary Conditions

Implemented in `src/simulation/BoundaryHandler.cpp`.

### 4.1 Inner boundary (planet surface, r = R)

When a parcel's position satisfies |**r**| < R after a Velocity Verlet step:
1. The position is **radially projected** back to the surface: **r** → R · **r̂**.
2. The radial component of velocity is **reflected** (only if the parcel is moving inward, v_r < 0):

\[
\mathbf{v}_{\rm rad,new} = -e_{\rm inner} \cdot v_{\rm rad}\,\hat{\mathbf{r}}, \quad \mathbf{v}_{\rm new} = \mathbf{v}_{\rm tan} + \mathbf{v}_{\rm rad,new}
\]

with `elasticityInner` = 1.0 (perfectly elastic). The tangential velocity is unchanged.

### 4.2 Outer boundary (top of atmosphere, r = R + H)

Analogous treatment when |**r**| > R + H:
1. Radial projection to r = R + H.
2. Outward radial velocity reflected with `elasticityOuter` = 1.0.

### 4.3 Physical interpretation and limitations

The boundaries represent a **hard impermeable shell**. The inner boundary approximates the planet's surface, and the outer boundary approximates an idealized rigid "lid" at the top of the atmosphere (analogous to a model top in GCMs). Both boundaries are currently perfectly elastic (no energy loss on collision), which means kinetic energy is conserved at impacts.

Limitations:
- Real atmosphere surfaces are not rigid; they exchange heat, moisture, and momentum with the land/ocean below.
- There is no topography, surface roughness, or land–sea contrast.
- The outer lid is not physical; real atmospheres transition gradually to space.
- A singularity at r = 0 is handled by a special case that projects the parcel to the north pole at r = R; this event is extremely rare in practice.

---

## 5. Numerical Integration

Implemented in `src/simulation/Integrator.cpp`.

### 5.1 Velocity Verlet algorithm

The simulation uses the **Velocity Verlet** (Störmer–Verlet) integrator with time step dt = 0.01 model units. Each call to `Integrator::step()` performs:

1. **First half-step velocity update:** \(\mathbf{v}(t + \tfrac{1}{2}dt) = \mathbf{v}(t) + \mathbf{a}(t)\,\tfrac{dt}{2}\)
2. **Full position update:** \(\mathbf{r}(t+dt) = \mathbf{r}(t) + \mathbf{v}(t+\tfrac{1}{2}dt)\,dt\)
3. **Apply boundary conditions** to **r**(t+dt).
4. **Rebuild the fine grid** with the new positions.
5. **Recompute accelerations a**(t+dt) from all forces.
6. **Second half-step velocity update:** \(\mathbf{v}(t+dt) = \mathbf{v}(t+\tfrac{1}{2}dt) + \mathbf{a}(t+dt)\,\tfrac{dt}{2}\)

### 5.2 Why Velocity Verlet is appropriate

Velocity Verlet is a second-order symplectic integrator. Its key advantages for particle dynamics are:
- **Energy conservation:** It is time-reversible and conserves a shadow Hamiltonian, so total energy does not drift systematically over long runs.
- **Simplicity:** It requires only one force evaluation per step (forces at the new positions are available for the next step's first half-step).
- **Stability:** For harmonic-like forces it is stable up to a critical dt; the choice dt = 0.01 with the soft-sphere stiffness k = 200 and max force = 100 appears numerically stable based on the observed 100,000-step run.

### 5.3 Stability considerations

The theoretical stability criterion for a harmonic oscillator with Velocity Verlet is dt < 2/ω, where ω = √(k/m). With k ≈ 200 and m = 1, this gives dt < 2/√200 ≈ 0.14, so dt = 0.01 provides a comfortable safety margin. The force limiter (maxForce = 100) prevents the stiffness from blowing up at very short separations, which further assists stability.

### 5.4 Stage 1 energy conservation test

`SimulationEngine::validateStage1()` includes a 1000-step energy conservation test with damping disabled. It requires total energy drift ≤ 1% to pass. This constitutes the primary numerical verification of the integrator.

---

## 6. Grid System

### 6.1 Fine grid (neighbor search)

Implemented in `src/simulation/FineGrid.cpp`.

The fine grid is a **3D spatial hash** (cell list) with cell size equal to the interaction cutoff σ = 2.0. Each cell stores the indices of all parcels whose positions map to that cell via:

```
cellIndex = floor(r / σ)   (component-wise)
```

For each parcel, pairwise repulsion forces are computed with all parcels in the **3×3×3 = 27 surrounding cells** (including the cell itself). This guarantees that no interacting pair (r < σ) is missed without needing an O(N²) all-pairs search.

### 6.2 Coarse grid (macroscopic diagnostics)

Implemented in `src/simulation/CoarseGrid.cpp`.

The coarse grid has cell size = 5 × σ = 10.0. It is rebuilt every 100 steps (and additionally whenever thermal collisions are applied). For each occupied coarse cell it computes:

| Quantity | Formula |
|---|---|
| Mean velocity | \(\mathbf{v}_{\rm mean} = \tfrac{1}{N_c}\sum_i \mathbf{v}_i\) |
| Kinetic temperature | \(T_{\rm kin} = \tfrac{1}{3N_c}\sum_i m|\mathbf{v}_i - \mathbf{v}_{\rm mean}|^2\) |
| Target temperature | \(T_{\rm target}(\theta, h)\) evaluated at the cell center |
| Mean specific humidity | \(q_{\rm mean} = \tfrac{1}{N_c}\sum_i q_{p,i}\) |

These macroscopic quantities feed the thermal collision engine and are written to `coarse_grid_step_*.csv`.

### 6.3 Performance benefit

Without a grid, pairwise force computation would cost O(N²) = 10⁸ operations per step. With the fine grid, only nearby parcels (within radius σ = 2.0 in a domain of radius 70) are checked, reducing the cost to approximately O(N · n_c) where n_c is the mean occupancy of neighboring cells — typically O(1)–O(10) for this density.

---

## 7. Thermal Physics

### 7.1 Target temperature field

Implemented in `src/simulation/Environment.cpp` (`computeTargetTemperatureSimplified`):

\[
T_{\rm target}(\theta, h) = T_{\rm base} + \Delta T \cos^2\!\theta - \Gamma \frac{h}{H}
\]

| Parameter | Symbol | Value |
|---|---|---|
| `baseTemperature` | T_base | 1.0 |
| `equatorPoleTemperatureContrast` | ΔT | 0.5 |
| `verticalCoolingGamma` | Γ | 0.2 |
| `atmosphereHeight` | H | 20.0 |

This creates:
- **Equator-to-pole heating:** Maximum T_target = 1.5 at the equator (θ = 0°), minimum = 1.0 at the poles (θ = ±90°) at the surface. The cos²θ shape loosely mimics the latitudinal dependence of incoming solar radiation.
- **Vertical lapse rate:** T_target decreases linearly with altitude at rate Γ/H = 0.01 model units per model-unit altitude. At the top of the atmosphere (h = H), T_target is reduced by Γ = 0.2 relative to the surface value.

Note: `useFullSolarHeating = false` in the current configuration. The parameter `solarFlux = 5000.0` is defined but **the full 3D solar-heating model is not implemented** in the current codebase; only the simplified formula above is used.

### 7.2 Thermal collisions

Implemented in `src/simulation/ThermalModel.cpp` and triggered from `SimulationEngine::applyThermalCollisions()`.

Thermal collisions begin at Phase 2 (step 20,001) and continue through Phase 3. They are applied every `thermalCollisionInterval` = 10 steps, with each parcel colliding stochastically with probability p_therm = 0.1 per event.

For each colliding parcel:

1. **Identify the coarse cell** and retrieve its mean velocity **v**_mean and target temperature T_target.
2. **Galilean shift** to the rest frame of the local mean flow: **v**_th = **v** − **v**_mean.
3. **Sample a Maxwell-Boltzmann reservoir velocity:**

\[
\mathbf{v}_{\rm res} \sim \mathcal{N}\!\left(0,\ \sigma_v^2\right)^3, \quad \sigma_v = \sqrt{\frac{T_{\rm target}}{m}}
\]

4. **Apply partial momentum exchange** with exchange coefficient α = `thermalExchangeAlpha` = 0.2:

\[
\mathbf{v}_{\rm th,new} = \mathbf{v}_{\rm th} + \alpha\,(\mathbf{v}_{\rm res} - \mathbf{v}_{\rm th})
\]

5. **Return to inertial frame:** **v**_new = **v**_mean + **v**_th,new.
6. **Update parcel temperature:**

\[
T_p = \frac{|\mathbf{v}_{\rm th,new}|^2}{3}
\]

**Physical interpretation:** This stochastic mechanism plays the role of radiative-thermal forcing. Parcels are nudged toward the local T_target at rate α, mimicking Newtonian relaxation toward an equilibrium temperature profile. It is a highly simplified substitute for radiative heating/cooling and sub-grid turbulent mixing.

**What is simplified:** Real thermal forcing in atmospheres involves radiative transfer (shortwave absorption, longwave emission), which depends on gas composition, cloud cover, and atmospheric optical depth. None of these are resolved here. The T_target field is also analytic and static — it does not respond to the circulation it drives.

---

## 8. Rotation and Circulation

### 8.1 Rotation activation

At the start of Phase 3 (step 40,001), the method `SimulationEngine::activateRotation()` imprints a solid-body rotation onto every parcel's velocity **exactly once**:

\[
v_x \mathrel{-}= \Omega\, y, \qquad v_y \mathrel{+}= \Omega\, x, \qquad v_z \text{ unchanged}
\]

with Ω = `angularVelocity` = 0.01 model units/step. This is equivalent to adding the co-rotation velocity **v**_rot = **Ω** × **r** = (−Ω y, Ω x, 0) to every parcel, seeding the entire atmosphere with the planet's spin in the inertial frame.

**This one-time imprint is not re-applied at subsequent steps.** No explicit Coriolis pseudo-force term is ever added to the equations of motion.

### 8.2 Why no explicit Coriolis force?

The simulation is formulated entirely in the **inertial (non-rotating) frame**. In this frame, the equations of motion are simply Newton's second law:

\[
m\ddot{\mathbf{r}} = \mathbf{F}_{\rm grav} + \mathbf{F}_{\rm rep} + \mathbf{F}_{\rm damp}
\]

with no fictitious forces. The Coriolis and centrifugal terms arise only when transforming to a rotating reference frame. Since the simulation remains in the inertial frame, Coriolis-like deflection of poleward-moving parcels emerges **naturally** from the conservation of angular momentum: a parcel moving away from the equator retains its initial eastward momentum from the rotation imprint but finds itself at a latitude where the local co-rotation speed is smaller, so it deflects eastward relative to the surface. This is the physical origin of the Coriolis effect; the code captures it without adding any artificial pseudo-force.

### 8.3 Circulation diagnostics

After step 50,000, the `CirculationAccumulator` bins all parcels into a 36-latitude × 20-altitude grid every 10 steps and accumulates the time-averaged meridional velocity v_θ and the proxy mass flux:

\[
\Phi_{\rm proxy}[{\rm lat, alt}] = N_{\rm bin} \cdot \langle v_\theta \rangle_{\rm bin}
\]

where N_bin is the particle count in the bin (serving as a density proxy). These averages feed the streamfunction calculator.

---

## 9. Spherical Diagnostics

Implemented in `src/utils/SphericalUtils.cpp` (`computeSphericalState`).

For each parcel, the Cartesian position and velocity are decomposed into spherical components as follows.

### 9.1 Coordinate definitions

| Quantity | Formula | Physical meaning |
|---|---|---|
| Radius | r = \|**r**\| | Distance from planet center |
| Altitude | h = r − R | Height above surface |
| Latitude | θ = arcsin(z/r) | Geographic latitude, range [−90°, +90°] |
| Longitude | φ = atan2(y, x) | Geographic longitude, range [−180°, +180°] |

### 9.2 Spherical unit vectors

\[
\hat{\mathbf{e}}_r = \frac{\mathbf{r}}{r}
\]

\[
\hat{\mathbf{e}}_\theta = (-\sin\theta\cos\phi,\ -\sin\theta\sin\phi,\ \cos\theta) \quad \text{(northward meridional)}
\]

\[
\hat{\mathbf{e}}_\phi = (-\sin\phi,\ \cos\phi,\ 0) \quad \text{(eastward zonal; undefined at poles where } \rho\to 0\text{)}
\]

where ρ = √(x²+y²) is the cylindrical radius.

### 9.3 Velocity projections

| Component | Formula | Physical meaning |
|---|---|---|
| v_r | **v** · **ê**_r | Radial (upwelling/downdraft) |
| v_θ | **v** · **ê**_θ | Meridional (north–south wind) |
| v_φ (inertial) | **v** · **ê**_φ | Zonal (east–west wind, inertial frame) |
| v_φ (relative) | (**v** − **v**_rot) · **ê**_φ | Zonal wind residual relative to solid-body rotation |

These components are written to `particle_spherical_step_*.csv` every 5,000 steps from Phase 3 onward.

---

## 10. Streamfunction Ψ

Implemented in `src/analysis/StreamfunctionCalculator.cpp`.

### 10.1 Physical motivation

The streamfunction Ψ(θ, h) is a standard diagnostic tool in atmospheric science for visualizing the **meridional overturning circulation** — the large-scale patterns of rising and sinking air that span the full latitude–altitude domain. Closed contours of Ψ indicate circulation cells; positive and negative values indicate opposite senses of rotation in the latitude–altitude plane.

### 10.2 Computation method

The streamfunction is defined here as the **vertical integral of the longitude-averaged, time-averaged meridional mass flux**. The computation proceeds in two stages:

**Stage 1 — Time averaging (CirculationAccumulator):**
From step 50,000 to 100,000, the accumulator bins all parcels every 10 steps into a 36 × 20 (latitude × altitude) grid. For each bin it computes the running mean:
\[
\langle v_\theta \rangle, \quad \Phi_{\rm proxy} = N_{\rm bin} \cdot \langle v_\theta \rangle
\]

**Stage 2 — Vertical integration (StreamfunctionCalculator):**
Let dh = H/N_alt = 20/20 = 1.0 model units. The streamfunction is integrated upward from the surface:

\[
\Psi[{\rm lat}][0] = \Phi_{\rm proxy}[{\rm lat}][0] \cdot dh
\]
\[
\Psi[{\rm lat}][{\rm alt}] = \Psi[{\rm lat}][{\rm alt}-1] + \Phi_{\rm proxy}[{\rm lat}][{\rm alt}] \cdot dh
\]

Empty bins (no particle samples) contribute zero mass flux to the integral; the running sum carries forward the last non-zero value, avoiding artificial discontinuities.

The result is written to `streamfunction_step_*.csv` and `streamfunction_summary.csv` every 5,000 steps from step 50,000 onward.

### 10.3 Sign convention

- **Positive Ψ** (Φ_proxy > 0 on average) corresponds to net northward meridional flow in that latitude–altitude region.
- **Negative Ψ** corresponds to net southward flow.
- Closed circulation cells (e.g., a Hadley-like cell) would appear as regions where Ψ transitions from positive to negative or vice versa with altitude.

### 10.4 Limitations

- The density proxy N_bin is a particle count, not a physical air density. It does not account for compressibility or altitude-dependent density weighting.
- The integration is purely kinematic; it does not enforce mass conservation in the Stokes streamfunction sense.
- Longitude averaging is performed implicitly through binning (each bin collects all longitudes for that latitude band), which is appropriate only if the circulation is approximately axisymmetric.
- **Hadley, Ferrel, or Polar cell labels should not be assigned** to the streamfunction output without strong supporting evidence of stable, spatially organized patterns over many averaging intervals. The current model does not reproduce Earth-like multi-cell structures and such labels would be premature.

---

## 11. Moisture Physics

The moisture cycle is implemented in `src/simulation/MoistureModel.cpp` (saturation physics), `src/simulation/ThermalModel.cpp` (humidity mixing), `src/simulation/SimulationEngine.cpp` (condensation, evaporation, water balance), and `src/simulation/CoarseGrid.cpp` (q_mean computation). All moisture features are enabled by default (`enableMoisture = true`, `enableMoisturePhysics = true`, etc.) and are active from the very first step of Phase 1 onward in the current configuration.

### 11.1 Specific humidity q_p

Each parcel carries a scalar `specificHumidity` (q_p, units kg/kg). It is transported passively with the parcel as it moves — there is no separate moisture advection equation; moisture simply goes wherever the parcel goes.

**Initialization** (`SimulationEngine::initializeParticles()`):

\[
q_p = \begin{cases}
q_{\rm surf} & h < h_{\rm low} \\[4pt]
q_{\rm surf}\,\exp\!\left(-\dfrac{h - h_{\rm low}}{h_{\rm scale}}\right) & h \ge h_{\rm low}
\end{cases}
\]

with:

| Parameter | Value | Meaning |
|---|---|---|
| `initialSurfaceSpecificHumidity` | 0.015 | Near-surface q_p |
| `humiditySurfaceLayerFraction` | 0.20 | h_low = 0.20 × H = 4.0 |
| `humidityDecayScaleFraction` | 0.30 | h_scale = 0.30 × H = 6.0 |

q_p is clamped to [0, 0.05] during initialization and at every update. The exponential decay profile approximates the real decrease of water vapor with altitude.

### 11.2 Saturation specific humidity q_sat

Implemented in `MoistureModel::saturationSpecificHumidity()` (`src/simulation/MoistureModel.cpp`).

**Step 1 — Model temperature to Kelvin:**
\[
T_K = T_{\rm ref,K} + T_{\rm scale}\,(T_{\rm model} - T_{\rm ref,model})
\]
\[
= 300 + 50\,(T_{\rm model} - 1.0)\ \text{K}, \quad \text{clamped to } [180,\ 330]\ \text{K}
\]

**Step 2 — Model altitude to meters:**
\[
h_m = \frac{h_{\rm model}}{H} \times H_{\rm phys} = \frac{h_{\rm model}}{20} \times 20{,}000\ \text{m}
\]

**Step 3 — Hydrostatic pressure profile:**
\[
p(h_m) = p_0\,\exp\!\left(-\frac{h_m}{H_s}\right) = 101{,}325\,\exp\!\left(-\frac{h_m}{8{,}500}\right)\ \text{Pa}
\]

**Step 4 — Saturation vapor pressure (Magnus/Buck formula):**
\[
e_{\rm sat}(T_K) = 611.2\,\exp\!\left(\frac{17.67\,(T_K - 273.15)}{T_K - 29.65}\right)\ \text{Pa}
\]

**Step 5 — Saturation specific humidity:**
\[
q_{\rm sat} = \frac{0.622\,e_{\rm sat}}{p - e_{\rm sat}}, \quad \text{clamped to } [0,\ 0.05]\ \text{kg/kg}
\]

**Numerical self-test** (run once at startup, `MoistureModel::runSaturationSelfTest()`): At T = 300 K, p = 101,325 Pa, the formula yields q_sat ≈ 0.0223 kg/kg, which falls in the accepted range [0.020, 0.030] kg/kg and matches standard meteorological reference values.

### 11.3 Humidity mixing during thermal collisions

Implemented in `ThermalModel::applyThermalCollision()` (`src/simulation/ThermalModel.cpp`).

Whenever a thermal collision event occurs (same stochastic gate as velocity exchange), humidity is relaxed toward the coarse-cell mean:

\[
q_p \mathrel{+}= \alpha_q\,\left(q_{\rm mean,cell} - q_p\right)
\]

The mixing coefficient α_q uses `humidityMixingAlpha`. Since this is set to −1.0, the code falls back to `thermalExchangeAlpha` = 0.2:

```cpp
double alphaQ = (config.humidityMixingAlpha >= 0.0)
              ? config.humidityMixingAlpha
              : config.thermalExchangeAlpha;
```

This represents diffusive moisture transport between parcels in the same macroscopic region, analogous to turbulent mixing of water vapor in the boundary layer. q_p is clamped to [0, 0.05] after each update.

**Conservation limitation:** This mixing step redistributes moisture among parcels in the same cell but does not globally conserve total humidity unless q_mean_cell is computed consistently from all parcels (which it is, via the coarse grid). However, because mixing is applied only to a randomly selected fraction of parcels per step, small accounting discrepancies can accumulate. These are tracked by the water balance diagnostics.

### 11.4 Evaporation

Implemented in `SimulationEngine::applyNearSurfaceEvaporation()` (`src/simulation/SimulationEngine.cpp`).

**Condition:** Active only for parcels in the near-surface layer:
\[
h < h_{\rm evap} = f_{\rm evap} \times H = 0.15 \times 20 = 3.0 \text{ model units}
\]

**Condition for evaporation:** parcel is subsaturated (q_p < q_sat).

**Rate formula:**
\[
\Delta q = k_{\rm evap}\,(q_{\rm sat} - q_p)\,dt = 0.001 \times (q_{\rm sat} - q_p) \times 0.01
\]

Clamped to [0, maxEvaporationDeltaQPerStep = 1×10⁻⁵] per step, and additionally limited by the room available before hitting the maximum q_p cap:
\[
\Delta q \le q_{\rm max} - q_p
\]

**Physical interpretation:** This mimics surface evaporation from an ocean or land surface: parcels near the surface absorb water vapor when they are drier than saturation. The linear rate law (proportional to humidity deficit) is a first-order kinetic approximation.

**Simplifications:**
- Uses the parcel's own temperature T_p as the evaporation surface temperature, not a dedicated surface temperature T_surface(θ). A future refinement noted in the code comment could use the latitudinally varying T_target instead.
- No ocean/land distinction; evaporation is uniform over the entire lower layer.
- No feedback: evaporation does not cool the surface.
- The rate coefficient k_evap = 0.001 and the cap maxEvaporationDeltaQPerStep = 1×10⁻⁵ are tuning parameters with no direct physical calibration.

### 11.5 Condensation

Implemented in `SimulationEngine::applyCondensation()` (`src/simulation/SimulationEngine.cpp`).

**Condition:** q_p > q_sat + ε (ε = supersaturationTolerance = 1×10⁻¹⁰).

**Amount:**
\[
\Delta q = \min(q_p - q_{\rm sat},\ \Delta q_{\rm max}), \quad \Delta q_{\rm max} = 10^{-4}
\]

q_p is reduced by Δq:
\[
q_p \mathrel{-}= \Delta q
\]

**Physical interpretation:** When a parcel becomes supersaturated (e.g., after ascending to cooler altitudes), excess water vapor condenses. The condensate is removed from the vapor phase and its latent heat is deposited into the parcel. There are no explicit liquid cloud droplets; the condensate is simply lost from the humidity budget.

**Simplifications:**
- No cloud microphysics (no droplet nucleation, growth, or fallout).
- No precipitation representation; condensed water does not fall back to the surface.
- The cap Δq_max = 10⁻⁴ per step prevents instantaneous full adjustment; in reality, condensation timescales depend on droplet growth kinetics.

### 11.6 Latent heat

When condensation occurs, the parcel temperature is increased:

\[
T_p \mathrel{+}= L_{\rm model} \cdot \Delta q, \quad L_{\rm model} = \text{latentHeatModelFactor} = 0.05
\]

**Why a model-scaled factor?** In real atmospheric physics, latent heating is characterized by L_v/c_p ≈ 2.5×10⁶ J/kg ÷ 1005 J/(kg·K) ≈ 2490 K per unit condensation (in SI units). However, in this model the temperature T_p is in dimensionless model units (typical value ~1.0) and Δq is in kg/kg (typical value ~10⁻⁴). Applying the SI ratio directly would produce negligible heating. The factor L_model = 0.05 is a dimensionless scaling parameter chosen to produce qualitatively meaningful heating in model units. It is not derived from first principles and its physical calibration is uncertain.

### 11.7 Water balance

Implemented in `SimulationEngine::updateWaterBalanceDiagnostics()` (`src/simulation/SimulationEngine.cpp`), written to `moisture_balance.csv`.

The diagnostics track:

| Quantity | Formula |
|---|---|
| `total_q` | Σ q_p (sum over all particles) |
| `initial_total_q` | Σ q_p at initialization |
| `cumulative_evaporation` | Running sum of all Δq_evap |
| `cumulative_condensation` | Running sum of all Δq_cond |
| `expected_total_q` | initial_total_q + cumulative_evaporation − cumulative_condensation |
| `water_balance_error` | total_q − expected_total_q |
| `water_balance_relative_error` | error / \|expected_total_q\| |

**Status flags:**
- `PASS`: \|error\| ≤ 1×10⁻⁸ OR \|relative error\| ≤ 1×10⁻⁶
- `WARNING`: otherwise (includes non-finite values)

**Physical importance:** A closed water balance confirms that moisture is neither created nor destroyed, only redistributed between evaporation, condensation, and transport. A WARNING status indicates that the humidity mixing step (Section 11.3) may introduce small discrepancies because it is applied stochastically to only a fraction of parcels per step, and the expected_total_q formula only accounts for evaporation and condensation, not diffusive mixing.

---

## 12. Simulation Phase Timing

The simulation is structured into three consecutive phases controlled by `SimulationConfig` step counters. It is important to understand that phases are **additive**: later phases do not disable earlier ones.

| Step range | Phase | Physics active |
|---|---|---|
| 1 – 20,000 | **Phase 1 (hydrostatic spin-up)** | Gravity + repulsion + damping (γ=100). Moisture physics (evaporation, condensation) also run from step 1 because `enableEvaporation` and `enableCondensation` are enabled in the config. |
| 20,001 – 40,000 | **Phase 2 (thermal forcing)** | Gravity + repulsion (damping disabled, γ=0). Stochastic thermal collisions every 10 steps nudge T_p toward T_target(θ,h). Evaporation and condensation continue. |
| 40,001 – 100,000 | **Phase 3 (rotation + circulation)** | All of Phase 2, **plus** a one-time rotational velocity imprint at step 40,001. Spherical diagnostics written every 5,000 steps. Circulation accumulation begins at step 50,000. Streamfunction written every 5,000 steps from step 50,000 onward. |

**Critically:**
- **Phase 2 thermal forcing does NOT stop at step 40,000.** Thermal collisions (`applyThermalCollisions`) continue to run every 10 steps throughout Phase 3, all the way to step 100,000.
- **At step 40,001, Phase 3 is added on top of Phase 2** — it does not replace it.
- The intended design described in comments and documentation suggests that Stage 4 (active moisture physics) should ideally begin only after a dry rotating circulation has had time to develop (e.g., from step 60,000 onward). However, in the current compiled configuration, moisture physics (`enableMoisture = true`) is active from step 1. Whether this is intentional or a configuration choice is not evident from the code alone.

---

## 13. Physical Phenomena Included

| Phenomenon | Included? | Implementation | Validation output |
|---|---|---|---|
| Hydrostatic shell geometry | Yes | Spherical boundary (R=50, H=20) enforced by `BoundaryHandler` | `simulation_log.csv` (shell bounds), Stage 1 bounds check |
| Density stratification | Yes (emergent) | Gravity + repulsion equilibrium in Phase 1 | Radial density profile in `Diagnostics::computeRadialDensityProfile()` |
| Particle–particle interaction | Yes | Soft-sphere repulsion in `ForceModel::computePairRepulsion()` | Energy conservation test |
| Radial gravity | Yes | `ForceModel::computeGravity()` | Shell bounds PASS |
| Equator-to-pole thermal gradient | Yes | T_target = T_base + ΔT·cos²θ in `Environment.cpp` | `temperature_zones.csv` (equatorial > polar T) |
| Vertical thermal lapse rate | Yes | −Γ·h/H term in T_target | `altitude_temperature_profile.csv` |
| Convective onset (qualitative) | Partially | Thermal collisions + T_target drive buoyancy-like overturning | Positive mean v_r at equator in `Diagnostics` Stage 2 check |
| Planetary rotation | Yes | One-time Ω×r imprint in `activateRotation()` | Mean speed before/after rotation printed to log |
| Inertial-frame Coriolis effect | Yes (emergent) | No pseudo-force; arises from conservation of angular momentum in inertial frame | Qualitative — visible in zonal velocity component v_φ |
| Meridional circulation | Partially (diagnostic) | Binned v_θ in `CirculationAccumulator` | `circulation_accum_step_*.csv` |
| Streamfunction Ψ | Yes (diagnostic) | Vertical integral of mass flux in `StreamfunctionCalculator` | `streamfunction_step_*.csv`, `streamfunction_summary.csv` |
| Moisture transport | Yes | q_p carried passively by parcels | `particles_step_*.csv` (q_p column) |
| Humidity mixing (diffusion) | Yes | q_p relaxed toward q_mean_cell during thermal collisions | `moisture_balance.csv` |
| Near-surface evaporation | Yes | Linear rate law in `applyNearSurfaceEvaporation()` | `evaporation_log.csv` |
| Condensation | Yes | Supersaturation removal in `applyCondensation()` | `condensation_log.csv` |
| Latent heat release | Yes | ΔT_p = L_model × Δq after condensation | `condensation_log.csv` (latent heating column) |
| Water balance accounting | Yes | Expected vs. actual total_q in `updateWaterBalanceDiagnostics()` | `moisture_balance.csv` (PASS/WARNING) |

---

## 14. Physical Phenomena Missing or Simplified

| Phenomenon | Status | Explanation |
|---|---|---|
| Full Navier–Stokes solver | Missing | The model uses discrete parcels with pairwise repulsion; no continuous pressure or viscosity field exists. |
| Real equation of state | Missing | There is no ideal-gas law p = ρRT. Pressure-like effects emerge from repulsion only. |
| Radiative transfer | Missing | T_target is a prescribed analytic field, not computed from solar/IR radiation. The `solarFlux` parameter is defined but the full solar heating model is not implemented. |
| Clouds as liquid particles | Missing | Condensate is removed from q_p without forming explicit cloud droplets. |
| Precipitation and rainout | Missing | No mechanism returns condensed water to the surface. |
| Ocean/land surface model | Missing | Evaporation is uniform over the entire near-surface layer regardless of geography. |
| Topography | Missing | The inner boundary is a perfect sphere; no mountains or basins. |
| Turbulence closure | Simplified | Sub-grid turbulence is approximated by the stochastic thermal collision mechanism, not a physical turbulence closure scheme (e.g., k-ε, Smagorinsky). |
| Real calibrated SI units | Simplified | Model units (R=50, H=20, g=0.016, T~1) are not directly comparable to Earth values except in the moisture module (which uses SI for saturation physics). |
| 1/r² gravity | Simplified | Gravity is constant g = 0.016 regardless of altitude; real gravity decreases with r². |
| Full 3D solar heating | Simplified | `useFullSolarHeating = false`; only the simplified analytic T_target(θ,h) is used. |
| Simplified evaporation model | Simplified | Uses parcel T_p as surface temperature proxy; no land–sea contrast; linear rate law; k_evap not physically calibrated. |
| Simplified condensation model | Simplified | Rate-limited by cap maxCondensationDeltaQPerStep = 10⁻⁴; no cloud microphysics. |
| Simplified latent heat scaling | Simplified | L_model = 0.05 is a dimensionless tuning factor, not derived from physical L_v/c_p in model units. |
| Imperfect water balance closure | Possible | Humidity mixing step is stochastic and partial; small accounting errors may accumulate, flagged as WARNING in `moisture_balance.csv`. |
| Real weather prediction | Missing | This is a research/educational model; no data assimilation, no forecast initialization. |

---

## 15. Validation Evidence

The following CSV outputs are produced by the simulation and support the claims made in this report.

| Output file | Content | What it validates |
|---|---|---|
| `particles_step_*.csv` | Per-parcel position, velocity, temperature, radius, speed, radial velocity, q_p | Particle positions within shell, velocity magnitudes, moisture distribution |
| `particle_spherical_step_*.csv` | Per-parcel r, θ, φ, v_r, v_θ, v_φ(inertial), v_φ(relative) | Spherical velocity structure, zonal flow pattern after rotation |
| `coarse_grid_step_*.csv` | Per-coarse-cell mean velocity, T_kin, T_target, q_mean | Macroscopic temperature field, wind field, humidity distribution |
| `temperature_zones.csv` | Step, T_equatorial, T_midlat, T_polar | Equator-to-pole thermal gradient (validates T_target forcing) |
| `altitude_temperature_profile.csv` | 20 altitude bins, mean T_kin per bin | Vertical lapse rate (validates T_target altitude cooling) |
| `simulation_log.csv` | KE, PE, total energy, min/max r, out-of-shell count | Energy conservation, shell containment |
| `circulation_accum_step_*.csv` | 36×20 grid: lat, alt, N, mean_v_theta, mass_flux | Time-averaged meridional circulation pattern |
| `streamfunction_step_*.csv` | 36×20 grid: lat, alt, Ψ | Overturning circulation structure (qualitative) |
| `streamfunction_summary.csv` | Step, max_abs_psi, min_psi, max_psi, cells_with_samples | Summary statistics of circulation strength |
| `evaporation_log.csv` | Step, evaporation_this_step, cumulative_evaporation, N_events | Near-surface moisture source |
| `condensation_log.csv` | Step, condensation_this_step, cumulative, latent_heating_this_step, cumulative_LH, N_events | Moisture sink, latent heat magnitude |
| `moisture_balance.csv` | Step, total_q, initial_q, cum_evap, cum_cond, expected_q, error, rel_error, status | Water conservation quality (PASS/WARNING) |

---

## 16. Limitations

1. **Simplified research/educational model.** This simulation captures several important qualitative atmospheric mechanisms — gravity-driven stratification, thermal forcing, rotation, and a moisture cycle — but it is not a complete atmospheric general circulation model. No quantitative prediction of real atmospheric behavior should be derived from it without careful validation.

2. **Physical interpretation depends on validation quality.** The thermal, moisture, and circulation results are meaningful only if the underlying dynamics have converged. Phase 1 must produce a stable stratified shell; Phase 2 must show a clear equatorial-warmer-than-polar temperature gradient; Phase 3 must show organized circulation patterns before streamfunction analysis is meaningful.

3. **Stage 4 moisture results should be interpreted cautiously.** If the `moisture_balance.csv` file reports a WARNING status at a given step, the water budget is not closed to within the specified tolerances, and the humidity mixing or condensation diagnostics for that step should be treated as approximate. A persistent PASS status is needed before making quantitative claims about the moisture cycle.

4. **Streamfunction cell labeling requires caution.** Hadley, Ferrel, and Polar circulation cell labels should not be applied unless the streamfunction pattern is stable across multiple output intervals, spatially organized, and physically consistent with the temperature and velocity fields. Transient patterns or noisy fields do not constitute evidence of real circulation cells.

5. **Model unit mismatch.** The moisture module uses SI-scaled physics (Magnus/Buck formula in Pa, Kelvin temperatures) bridged to model units via a linear scaling with T_scale = 50 K per model-unit. The accuracy of this bridge depends on whether the model temperature field spans a physically reasonable range of ~50 K around the 300 K reference. If the model temperatures drift significantly from 1.0 in model units, the saturation physics may operate outside its physically calibrated range.

6. **OpenMP parallelism.** The CMakeLists.txt links with OpenMP if available. The current source code does not contain explicit `#pragma omp` directives; therefore OpenMP may not actually parallelize the computation unless the compiler auto-vectorizes loops. This does not affect physics results but is relevant to performance.

---

## 17. Conclusion

AtmosphericSimulation implements a simplified particle-based atmospheric model that combines mechanical parcel interactions (soft-sphere repulsion, gravity), damped hydrostatic spin-up, stochastic Newtonian thermal forcing toward a latitude/altitude-dependent target temperature, one-time planetary rotation seeding in the inertial frame, spherical-coordinate circulation diagnostics including a streamfunction, and a four-component moisture cycle (specific humidity transport, saturation physics, evaporation, condensation with latent heating, and water balance accounting).

The model captures several important qualitative atmospheric mechanisms:
- Gravity-driven density stratification in a spherical shell.
- An equator-to-pole thermal gradient that drives meridional overturning.
- Inertial-frame Coriolis-like deflection emerging naturally from angular momentum conservation after rotation activation.
- A simplified water vapor cycle with physically motivated saturation physics (Magnus/Buck formula) and diagnostic water balance monitoring.

However, it does not replace a full continuum atmospheric model. It lacks a true pressure equation of state, radiative transfer, cloud microphysics, precipitation, surface exchange processes, and turbulence closure. Its physical unit system is internally consistent but not calibrated to Earth atmosphere values (except in the moisture saturation calculation). Results should be interpreted as qualitative illustrations of atmospheric dynamics principles rather than quantitative atmospheric predictions.

---

## Appendix A: Files Inspected

| File | Lines | Role |
|---|---|---|
| `src/main.cpp` | 9 | Entry point |
| `src/model/SimulationConfig.h` | ~200 | All simulation parameters |
| `src/model/Parcel.h` | 18 | Parcel state definition |
| `src/model/Vec3.h` | ~50 | 3D vector math |
| `src/utils/Constants.h` | 8 | Unused gravity constant |
| `src/utils/SphericalUtils.h` | 20 | SphericalState struct |
| `src/utils/SphericalUtils.cpp` | 87 | Cartesian→spherical decomposition |
| `src/io/ConfigReader.h` | 8 | Stub (empty) |
| `src/io/OutputWriter.h` | ~101 | CSV writer declarations |
| `src/io/OutputWriter.cpp` | ~456 | All CSV output implementations |
| `src/simulation/ForceModel.h` | 64 | Gravity, repulsion, damping (header-only) |
| `src/simulation/Environment.h` | — | T_target declarations |
| `src/simulation/Environment.cpp` | 52 | T_target formula |
| `src/simulation/FineGrid.h` | — | Neighbor-search declarations |
| `src/simulation/FineGrid.cpp` | 54 | Cell-list spatial hash |
| `src/simulation/CoarseGrid.h` | — | Macroscopic cell declarations |
| `src/simulation/CoarseGrid.cpp` | 101 | Mean v, T_kin, T_target, q_mean per cell |
| `src/simulation/BoundaryHandler.h` | — | Boundary declarations |
| `src/simulation/BoundaryHandler.cpp` | 68 | Radial elastic reflection |
| `src/simulation/Integrator.h` | — | Integrator declarations |
| `src/simulation/Integrator.cpp` | 68 | Velocity Verlet + force assembly |
| `src/simulation/ThermalModel.h` | — | Thermal model declarations |
| `src/simulation/ThermalModel.cpp` | 67 | Maxwell-Boltzmann thermal collisions + humidity mixing |
| `src/simulation/MoistureModel.h` | — | Moisture function declarations |
| `src/simulation/MoistureModel.cpp` | 138 | Magnus/Buck saturation, T→K scaling, pressure profile |
| `src/simulation/SimulationEngine.h` | ~118 | Engine declarations |
| `src/simulation/SimulationEngine.cpp` | 671 | Phase orchestration, condensation, evaporation, water balance |
| `src/analysis/Diagnostics.h` | — | Diagnostics declarations |
| `src/analysis/Diagnostics.cpp` | ~200 | Radial density, zone temperatures, energy |
| `src/analysis/CirculationAccumulator.h` | — | Accumulator declarations |
| `src/analysis/CirculationAccumulator.cpp` | 152 | Meridional mass flux binning |
| `src/analysis/StreamfunctionCalculator.h` | — | Streamfunction declarations |
| `src/analysis/StreamfunctionCalculator.cpp` | 108 | Vertical integration of mass flux |
| `CMakeLists.txt` | 26 | Build configuration |

---

## Appendix B: Main Physics Features Confirmed in Code

1. Spherical shell domain: R = 50, H = 20, valid for R ≤ r ≤ R + H.
2. Radial gravity: **F** = −m g **r̂**, g = 0.016.
3. Soft-sphere repulsion: F = k(σ² − r²) for r < σ = 2.0, k = 200, capped at 100.
4. Phase 1 damping: **F** = −γ m (**v** − **Ω** × **r**), γ = 100 for steps 1–20,000, then γ = 0.
5. Velocity Verlet integration: dt = 0.01.
6. Fine grid cell list: cell size σ = 2.0, 27-neighbor stencil.
7. Coarse grid: cell size 5σ = 10.0; computes v_mean, T_kin, T_target, q_mean.
8. Target temperature: T_base + ΔT·cos²θ − Γ h/H with T_base=1, ΔT=0.5, Γ=0.2.
9. Stochastic thermal collisions: Maxwell-Boltzmann reservoir, α = 0.2, every 10 steps.
10. One-time rotation imprint at step 40,001: v += **Ω** × **r**, Ω = 0.01.
11. Spherical velocity diagnostics: v_r, v_θ, v_φ in inertial and rotating frames.
12. Circulation accumulation: 36×20 grid, from step 50,000, every 10 steps.
13. Streamfunction: upward integral Ψ[alt] = Ψ[alt−1] + Φ_proxy · dh.
14. Specific humidity q_p: per-parcel scalar, initialized with exponential altitude profile.
15. Saturation humidity: Magnus/Buck formula with hydrostatic pressure model.
16. Humidity mixing during collisions: q_p += α_q (q_mean − q_p), α_q = 0.2.
17. Near-surface evaporation: h < 3.0, rate k_evap = 0.001, capped at 10⁻⁵ per step.
18. Condensation: q_p − q_sat, capped at 10⁻⁴ per step; removes vapor.
19. Latent heating: ΔT_p = 0.05 × Δq after condensation.
20. Water balance: tracks initial_q + cumulative_evap − cumulative_cond vs. total_q.

---

## Appendix C: Missing or Simplified Physics

1. No full Navier–Stokes solver (no continuous pressure field).
2. No real equation of state (no ideal-gas p = ρRT).
3. No radiative transfer (`useFullSolarHeating = false`; T_target is prescribed).
4. No cloud liquid water phase (condensate disappears from q_p).
5. No precipitation or rainout.
6. No ocean/land surface model; evaporation is spatially uniform.
7. No topography.
8. No physical turbulence closure; sub-grid mixing approximated by stochastic thermal collisions.
9. No real calibrated Earth SI units (except in moisture saturation physics).
10. Gravity is constant with altitude (no 1/r² falloff).
11. Simplified latent heat factor L_model = 0.05 (not derived from physical L_v/c_p in model units).
12. Possible imperfect water balance closure due to stochastic humidity mixing.
13. `Constants.h` defines GRAVITY = 9.81 but this constant is never used in the simulation.
14. `solarFlux = 5000.0` is defined in the config but no solar heating model is implemented.

---

## Appendix D: Uncertainties and Ambiguities

1. **Moisture physics active from step 1:** The config has `enableMoisture = true` and `enableCondensation = true` from initialization, meaning moisture physics runs during Phase 1 (hydrostatic spin-up) alongside damping. The simulation documentation suggests Stage 4 should start later (after ~60,000 steps), but the code does not gate moisture on a step threshold. Whether this is intentional is not determined from the code alone.

2. **Water balance at non-zero WARNING:** The water balance formula `expected = initial + evap − cond` accounts only for the evaporation and condensation fluxes, not for the humidity mixing redistribution in thermal collisions. Because mixing conserves total humidity (it exchanges between parcels within a cell) only approximately (stochastic partial application), small residuals are expected. The PASS/WARNING threshold values (abs: 10⁻⁸, rel: 10⁻⁶) are quite strict, and WARNING statuses do not necessarily indicate a serious problem.

3. **solarFlux parameter:** The config defines `solarFlux = 5000.0` and `useFullSolarHeating = false`. No code was found that reads `solarFlux` in any computational path. This parameter appears to be reserved for a future stage.

4. **Stage 1 damping and v_rot direction:** The damping force targets `v_rot = (−Ωy, Ωx, 0)`, which is the equatorial co-rotation velocity for rotation about the z-axis only. This implicitly defines the planet's rotation axis as the z-axis. There is no explicit documentation of this convention in the code comments, though it is consistent with the latitude definition z/r = sin θ.

5. **OpenMP parallelism:** CMakeLists.txt links OpenMP if found. No `#pragma omp parallel` directives were identified in the source files read. If auto-parallelism is not active, the simulation runs single-threaded. This does not affect physics.
