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

### PCS / BESS Inverter

- Receives a setpoint in percent of nominal power.
- Valid setpoint range: `-100..100%`
- Positive power means discharge.
- Negative power means charge.
- At this stage there is no SOC model, no efficiency model, and no battery energy capacity limit.

### Grid Meter

- Shows instantaneous active power exchange with the grid.
- Positive value means export to grid.
- Negative value means import from grid.
- The grid license limit is displayed for visibility only.

### PV Meter

- Shows instantaneous active power produced by the PV inverter.

### BESS Meter

- Shows instantaneous active power of the PCS / BESS inverter.

### Local Load

- Local load is an internal site load.
- Valid range is `>= 0`
- It always consumes power.
- It must be configurable from the HMI.

## Units

- Power: `kW`
- Setpoints: `%`
- Pyranometer: `W/m2`
- Nominal inverter powers: `kW`

## Input Limits

- `PV setpoint`: clamp to `0..100`
- `PCS setpoint`: clamp to `-100..100`
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
P_bess_actual = BESS_nominal * PCS_setpoint / 100
```

Grid power:

```text
P_grid = P_pv_actual + P_bess_actual - P_load
```

Interpretation:

- `P_grid > 0` means export to grid
- `P_grid < 0` means import from grid

## Example Scenarios

### Scenario 1

- `PV_nominal = 20000 kW`
- `BESS_nominal = 10000 kW`
- `PV_setpoint = 50%`
- `PCS_setpoint = 0%`
- `pyranometer = 1500`
- `P_load = 0`

Results:

- `P_pv_actual = 10000 kW`
- `P_bess_actual = 0 kW`
- `P_grid = 10000 kW`

### Scenario 2

- `PV_nominal = 20000 kW`
- `PV_setpoint = 80%`
- `PCS_setpoint = 0%`
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
- `PCS_setpoint = -30%`
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
- `PCS_setpoint = -80%`
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
- `PCS_setpoint = 0%`
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

## Planned Modbus Variables

### PV Inverter

- `pv_setpoint_pct`
- `pv_nominal_power_kw`
- `pv_actual_power_kw`
- `pv_available_power_kw`
- `pv_enable`
- `pv_status`

### PCS / BESS Inverter

- `pcs_setpoint_pct`
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

