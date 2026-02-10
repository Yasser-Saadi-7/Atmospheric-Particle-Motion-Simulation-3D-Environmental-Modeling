# Atmospheric Particle Motion Simulation (Phase A)
**Simulation of Atmospheric Particle Movement – A Framework for Modeling Air Parcel Dynamics**

This repository contains the **Phase A** deliverables for a final project at **Braude College of Engineering**.  
The project designs a **molecular-dynamics-inspired Lagrangian framework** for simulating air-parcel motion in a rotating, thermodynamically forced atmosphere.

> **Key principle:** Large-scale circulation is **not imposed** as a prescribed background wind field.  
> Instead, macroscopic transport patterns are expected to **emerge** from the collective particle dynamics under thermal forcing and rotation, and are diagnosed from particle statistics.

---

## Project Overview
We model the atmosphere as a set of interacting **coarse-grained air parcels** (particles).  
Each parcel carries its own state:
- Position and velocity: \( \mathbf{x}(t), \mathbf{v}(t) \)
- Optional thermodynamics: \( T(t), q(t), P(t), \rho(t) \)

The parcel dynamics are advanced in time using an MD-style integrator, while global-scale patterns are obtained by **diagnostics** (binning/averaging parcel velocities) rather than being injected as external winds.

---

## Physical Model (High Level)
Parcel motion follows Newton’s second law in a rotating reference frame:

\[
\frac{d\mathbf{x}}{dt} = \mathbf{v}
\]
\[
m\frac{d\mathbf{v}}{dt} = \mathbf{F}_g + \mathbf{F}_b + \mathbf{F}_d + \mathbf{F}_{cor} + \mathbf{F}_{int}
\]

Where:
- Gravity:
\[
\mathbf{F}_g = - m g \mathbf{k}
\]
- Buoyancy (from parcel–environment density contrast):
\[
\mathbf{F}_b = V(\rho_{env} - \rho_{parcel}) g \mathbf{k}
\]
- Linear drag:
\[
\mathbf{F}_d = - C_d \mathbf{v}
\]
- Coriolis force:
\[
\mathbf{F}_{cor} = -2m(\boldsymbol{\Omega} \times \mathbf{v})
\]
- Inter-parcel interactions (pressure-like coupling, local neighborhood):
\[
\mathbf{F}_{int,i} = \sum_{j \ne i} -\nabla_{\mathbf{x}_i} V(r_{ij}), \quad r_{ij} = \lVert \mathbf{x}_i - \mathbf{x}_j \rVert
\]

Thermal forcing is represented via Newtonian relaxation toward a target profile:
\[
\frac{dT}{dt} = -\frac{T - T_{eq}(\phi, z)}{\tau}
\]

Optional moist processes (condensation + latent heating) are planned for Phase B.

---

## Scaled Virtual Environment (Target Configuration)
To support meaningful emergence diagnostics, Phase A defines a scalable domain with a target regime such as:
- Planetary radius: **\(R \sim 1000\,km\)**
- Atmospheric depth: **\(H \sim 10{-}20\,km\)**
- Particle count: **\(N \sim 20,000{-}50,000\)** (or higher if feasible)
- Rotation: prescribed via period \(P\), with \(\Omega = 2\pi/P\)

Final values will be selected in Phase B using stability, profiling, and convergence tests.

---

## Numerical Method
Time integration is planned using **Velocity-Verlet** (common in MD).  
The timestep \(dt\) is treated as a tunable parameter:
- A small \(dt\) may be used for prototype/debug runs
- A retuned \(dt\) will be selected for the target configuration using stability tests and convergence checks

---

## Diagnostics: How “Emergent Circulation” Is Measured
Since no background wind is imposed, circulation is diagnosed from the particles:
- Bin parcels in **latitude–altitude** space \((\phi, z)\)
- Compute mean velocity fields:
  - \(\overline{\mathbf{v}}(\phi, z)\)
- Look for statistically stable structures resembling:
  - Hadley/Ferrel/Polar-like cells
  - jet-like zonal flows

---

## Tools & Technologies (Planned)
- **C++** (core simulation engine)
- **OpenMP** for multi-core parallelism
- Neighbor search acceleration (e.g., **cell lists / spatial hashing**) for interaction cutoff
- Output files for post-processing + visualization (format to be finalized in Phase B)

> Any post-processing tools will be treated as optional and separate from the engine.

---

## Repository Structure (Suggested / Phase A)
