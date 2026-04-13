# ACcouplingSimulator Specification

## Purpose

This project simulates an AC-coupled energy system with:

- one `PV inverter`
- one `PCS / BESS inverter`
- one `Grid meter`
- one `PV meter`
- one `BESS meter`
- one web HMI for monitoring and changing simulation parameters

The simulator is intended to behave like a real-time test bench for an external third-party controller that sends setpoints over Modbus TCP.

## Main Principles

- The simulator must execute external setpoints as they are sent.
- The simulator must not automatically enforce the grid license limit.
- The `grid license limit` is informational only at this stage.
- The `PCS` setpoint has priority over trying to stay below the grid license limit.
- The system reacts in real time with a simulation step of `1 second`.
- Device response is not instantaneous. The target behavior is a smooth first-order style response with an effective response time of about `2 seconds`.

## Devices

### PV Inverter

- Receives a setpoint in percent of nominal power.
- Valid setpoint range: `0..100%`
- Negative setpoints are not allowed.
- Actual PV power is limited both by the setpoint and by solar availability from the pyranometer.
- PV nominal power is currently editable at runtime from the HMI.
- Supports reactive control in one active mode at a time:
  - reactive power mode
  - cos phi mode
- Reactive setpoint range: `-100..100%` of PV nominal power
- Cos phi setpoint range: `-1..1`
- If reactive control mode is `0`, reactive power setpoint has priority.
- If reactive control mode is `1`, cos phi setpoint is used to derive reactive power.

### PCS / BESS Inverter

- Receives an active power setpoint directly in `kW`.
- Valid setpoint range: `-PCS_nominal..+PCS_nominal`
- Positive power means discharge.
- Negative power means charge.
- At this stage there is no SOC model, no efficiency model, and no battery energy capacity limit.
- PCS / BESS nominal power is currently editable at runtime from the HMI.

### Grid Meter

- Shows instantaneous active power exchange with the grid.
- Positive value means export to grid.
- Negative value means import from grid.
- The grid license limit is displayed for visibility only.
- Also shows reactive power, cos phi, and voltage.

### PV Meter

- Shows instantaneous active power produced by the PV inverter.
- Also shows reactive power, cos phi, and voltage.

### BESS Meter

- Shows instantaneous active power of the PCS / BESS inverter.
- Reactive power is currently fixed at `0`.
- Voltage is currently fixed at the base voltage.
- Cos phi is currently fixed at `1.0`.

### Local Load

- Local load is an internal site load.
- Valid range is `>= 0`
- It always consumes power.
- It must be configurable from the HMI.

## Runtime-Editable Parameters In HMI

The current HMI can change these values at runtime:

- `PV setpoint`
- `PCS setpoint`
- `PV nominal power`
- `PCS nominal power`
- `PV reactive power setpoint`
- `PV cos phi setpoint`
- `reactive control mode`
- `pyranometer`
- `local load`
- `grid license limit`
- `voltage min`
- `voltage max`
- `PV enabled`
- `BESS enabled`

The current HMI layout is organized for live observation:

- grouped live summaries for `PV Meter`, `BESS Meter`, `Grid Meter`, and `Simulation`
- shared trend graph for `PV`, `BESS`, and `Grid`
- live alarms for:
  - `Grid meter exceeded license`
  - `Grid meter is importing from grid`
- a separate Modbus configuration page

## Units

- Power: `kW`
- PV setpoint: `%`
- PCS setpoint: `kW`
- Pyranometer: `W/m2`
- Nominal inverter powers: `kW`

## Input Limits

- `PV setpoint`: clamp to `0..100`
- `PCS setpoint`: clamp to `-PCS_nominal..+PCS_nominal`
- `pyranometer`: clamp to `0..1500`
- `local load`: clamp to `>= 0`

## Pyranometer Rule

- Pyranometer range is `0..1500 W/m2`
- `1500 W/m2` corresponds to full available PV nominal power

PV available power:

```text
P_pv_available = PV_nominal * pyranometer / 1500
```

## Power Sign Convention

- `PV power > 0`: PV generation
- `PV power = 0`: no PV generation
- `BESS power > 0`: battery discharging
- `BESS power < 0`: battery charging
- `Grid power > 0`: export to grid
- `Grid power < 0`: import from grid
- `Load power >= 0`: local consumption
- `Q > 0`: lowers voltage
- `Q < 0`: raises voltage

## Core Equations

PV target power:

```text
P_pv_target = PV_nominal * PV_setpoint / 100
```

PV available power:

```text
P_pv_available = PV_nominal * pyranometer / 1500
```

PV actual power:

```text
P_pv_actual = min(P_pv_target, P_pv_available)
```

BESS actual power:

```text
P_bess_actual = clamp(PCS_setpoint_kw, -BESS_nominal, +BESS_nominal)
```

PV reactive power in reactive power mode:

```text
Q_pv_target = PV_nominal * Q_setpoint_pct / 100
```

PV reactive power in cos phi mode:

```text
Q_pv_target = sign(cos_phi) * sqrt((P_pv_actual / abs(cos_phi_limited))^2 - P_pv_actual^2)
```

Where:

- `abs(cos_phi_limited) >= 0.01`
- `cos_phi > 0 -> Q > 0`
- `cos_phi < 0 -> Q < 0`

Grid power:

```text
P_grid = P_pv_actual + P_bess_actual - P_load
```

Grid reactive power:

```text
Q_grid = Q_pv + Q_bess
```

At the current stage:

- `Q_bess = 0`

Interpretation:

- `P_grid > 0` means export to grid
- `P_grid < 0` means import from grid

## Cos Phi Rules

- Cos phi sign follows reactive power sign
- If `P = 0`, cos phi is reported as `1.0`
- If `Q = 0`, cos phi is reported as `1.0`

## Voltage Rules

- Voltage is modeled linearly
- Default range is `20..24 kV`
- `V_base = (V_min + V_max) / 2`
- `Q = -100% -> V = V_max`
- `Q = 0 -> V = V_base`
- `Q = +100% -> V = V_min`

At the current stage:

- `V_pv` depends on `Q_pv`
- `V_bess = V_base`
- `V_grid` depends on `Q_grid`

## Example Scenarios

### Scenario 1

- `PV_nominal = 20000 kW`
- `BESS_nominal = 10000 kW`
- `PV_setpoint = 50%`
- `PCS_setpoint = 0 kW`
- `pyranometer = 1500`
- `P_load = 0`

Results:

- `P_pv_actual = 10000 kW`
- `P_bess_actual = 0 kW`
- `P_grid = 10000 kW`

### Scenario 2

- `PV_nominal = 20000 kW`
- `PV_setpoint = 80%`
- `PCS_setpoint = 0 kW`
- `pyranometer = 750`
- `P_load = 0`

Results:

- `P_pv_target = 16000 kW`
- `P_pv_available = 10000 kW`
- `P_pv_actual = 10000 kW`
- `P_grid = 10000 kW`

### Scenario 3

- `PV_nominal = 20000 kW`
- `BESS_nominal = 10000 kW`
- `PV_setpoint = 50%`
- `PCS_setpoint = -3000 kW`
- `pyranometer = 1500`
- `P_load = 0`

Results:

- `P_pv_actual = 10000 kW`
- `P_bess_actual = -3000 kW`
- `P_grid = 7000 kW`

### Scenario 4

- `PV_nominal = 20000 kW`
- `BESS_nominal = 10000 kW`
- `PV_setpoint = 20%`
- `PCS_setpoint = -8000 kW`
- `pyranometer = 1500`
- `P_load = 0`

Results:

- `P_pv_actual = 4000 kW`
- `P_bess_actual = -8000 kW`
- `P_grid = -4000 kW`

### Scenario 5

- `PV_nominal = 20000 kW`
- `BESS_nominal = 10000 kW`
- `PV_setpoint = 50%`
- `PCS_setpoint = 0 kW`
- `pyranometer = 1500`
- `P_load = 6000`

Results:

- `P_pv_actual = 10000 kW`
- `P_bess_actual = 0 kW`
- `P_grid = 4000 kW`

## Modbus TCP Devices

Planned logical devices:

1. `PV inverter`
2. `PCS / BESS inverter`
3. `Grid meter`
4. `PV meter`
5. `BESS meter`
6. `Simulation controller`

The simulation controller is not a physical device. It exists to expose simulation inputs such as pyranometer and local load.
It also exposes shared simulation settings such as reactive control mode and voltage limits.

## Planned Modbus Variables

### PV Inverter

- `pv_setpoint_pct`
- `pv_nominal_power_kw`
- `pv_actual_power_kw`
- `pv_available_power_kw`
- `pv_enable`
- `pv_status`

### PCS / BESS Inverter

- `pcs_setpoint_kw`
- `pcs_nominal_power_kw`
- `pcs_actual_power_kw`
- `pcs_enable`
- `pcs_status`

### Grid Meter

- `grid_active_power_kw`
- `grid_license_limit_kw`
- `grid_limit_exceeded`
- `grid_direction`

### PV Meter

- `pv_meter_active_power_kw`

### BESS Meter

- `bess_meter_active_power_kw`

### Simulation Controller

- `pyranometer_wm2`
- `local_load_kw`
- `simulation_enable`
- `simulation_step_sec`
- `response_time_ms`

## What Is Intentionally Out of Scope For Now

- SOC
- battery energy capacity
- charge and discharge efficiency
- accumulated energy counters
- automatic export limiting based on grid license
- fault simulation beyond simple placeholder statuses

## Recommended Next Implementation Steps

1. Create a small simulation core with a one-second update loop.
2. Implement device state models for PV, PCS, and meters.
3. Centralize configuration in a text file.
4. Expose Modbus TCP servers for each logical device.
5. Add a minimal web HMI for live values and parameter changes.
