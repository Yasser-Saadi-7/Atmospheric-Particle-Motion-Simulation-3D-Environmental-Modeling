# Simulation of Atmospheric Particle Movement
**A Framework for Modeling Air Parcel Dynamics (Phase A)**

## Overview
This project develops a research-oriented simulation framework for modeling air parcel motion in a planetary atmosphere using a Lagrangian, molecular-dynamics-inspired approach. The simulator tracks a large ensemble of interacting parcels, each carrying its own kinematic and thermodynamic state. Unlike trajectory models driven by a prescribed wind field, large-scale transport and circulation patterns are expected to emerge from particle dynamics under thermal forcing and rotation, and are diagnosed from particle statistics.

## Core Concept: MD-Inspired Emergent Circulation
- No imposed background wind field.
- Global-scale circulation is treated as an emergent outcome of:
  - Particle–particle interactions (pressure-like behavior).
  - Gravity, buoyancy, and drag.
  - Thermal forcing via relaxation toward a target temperature profile.
  - Rotation in a rotating reference frame.

## Model State (Per Parcel)
- Position and velocity: x(t), v(t)
- Thermodynamics: T(t), q(t), P(t), ρ(t)

## Equations of Motion
The dynamics are formulated as an ODE system advanced in time:

**Kinematics**
- dx/dt = v

**Momentum**
- m dv/dt = Fg + Fb + Fd + Fcor + Fint

### Forces
**Gravity**
- Fg = −m g k

**Buoyancy**
- Fb = V (ρenv − ρparcel) g k

**Linear Drag**
- Fd = −Cd v
- Cd can be set via a damping timescale τd: Cd = m/τd

**Coriolis (Rotating Frame)**
- Fcor = −2 m (Ω × v)

**Inter-Parcel Interaction (Pressure-Like, Short-Range)**
- Fint,i = Σj≠i ( −∇xi V(rij) )
- rij = |xi − xj|
- V(r) is a repulsive potential with cutoff radius rc to keep interactions local.

## Thermal Forcing (Simplified Radiative Effects)
Radiative heating/cooling is represented by Newtonian relaxation toward a target temperature profile Teq(φ, z):

- dT/dt = −(T − Teq)/τ

This provides a controlled, computationally efficient forcing that can drive large-scale organization when combined with rotation and interactions.

## Moist Processes
Each parcel can carry specific humidity q. Saturation and condensation are modeled using simplified parameterizations:
- Condensation is triggered when q > qsat(T, P).
- Latent heating increases temperature and buoyancy.
This enables controlled dry vs moist experiments.

## Virtual Environment and Scaling
The simulation supports two operating modes:
1) Prototype/debug configuration (small and fast)
2) Target configuration (large enough to diagnose global circulation patterns)

Target-scale guidelines (design goal):
- Planetary radius R ~ 1000 km
- Atmospheric depth H ~ 10–20 km
- Number of parcels N ~ 20,000–50,000 (or higher if feasible)
- Rotation period P is chosen to preserve dynamically meaningful rotation effects.

Final parameter values are refined using stability tests, profiling, and convergence checks.

## Numerical Integration
The system is advanced using an explicit Velocity-Verlet integrator (standard in molecular dynamics). A prototype time step (e.g., dt = 0.1 s, scaled) is used initially and then re-tuned for the target configuration based on stability and sensitivity tests.

## Software and Performance
- Language: C++
- Parallelization: OpenMP (multi-core acceleration)
- Implementation focus:
  - efficient neighbor search (e.g., cell lists),
  - scalable force evaluation for short-range interactions,
  - reproducible experiments and diagnostics.

## Outputs and Diagnostics
The simulator produces time-resolved parcel trajectories and thermodynamic variables for post-processing. Macroscopic circulation is diagnosed statistically by binning parcels (e.g., latitude–altitude bins) and computing mean velocity fields and circulation indicators to assess whether cell-like structures and jets emerge.

## Validation Plan (Phase A)
Validation includes:
- Numerical stability: compare runs with dt and dt/2 and require convergence.
- Benchmark tests:
  - gravity-only free fall,
  - drag relaxation,
  - Coriolis-only inertial motion,
  - moist saturation adjustment (when enabled).
- Sensitivity analysis over key parameters (Cd, τ, τd, rc, etc.).
- Performance scaling with increasing N and neighbor-search acceleration.


## Team
- Yasser Sadi
- Diana Hujerat  
Advisor: Dr. Zakharia Frenkel

## Repository
Atmospheric-Particle-Motion-Simulation-3D-Environmental-Modeling
