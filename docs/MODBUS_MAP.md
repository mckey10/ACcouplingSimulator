# Modbus Map

This document describes the current Modbus TCP register map implemented by the simulator.

## General Rules

- Each logical device runs on its own Modbus TCP port.
- Register addresses below are zero-based protocol addresses.
- Human-friendly Modbus notation would be:
  - holding register `0` -> `40001`
  - input register `0` -> `30001`
- Most numeric values use signed `int32`, split into two 16-bit registers.
- Word order is big-endian:
  - register `N` = high word
  - register `N+1` = low word
- `FC3` reads holding registers.
- `FC4` reads input registers.
- `FC6` writes only 16-bit single-register values.
- `FC16` must be used for 32-bit values such as powers, setpoints, pyranometer, and load.

## Device Endpoints

- `PV inverter`: `127.0.0.1:15001`, unit id `1`
- `PCS inverter`: `127.0.0.1:15002`, unit id `2`
- `Grid meter`: `127.0.0.1:15003`, unit id `3`
- `PV meter`: `127.0.0.1:15004`, unit id `4`
- `BESS meter`: `127.0.0.1:15005`, unit id `5`
- `Simulation controller`: `127.0.0.1:15010`, unit id `10`

## Scaling

- Power values: `kW x 10`
- Percent values: `% x 100`
- Pyranometer: `W/m2 x 1`
- Enable/status flags: `0` or `1`

## PV Inverter

### Holding Registers

- `0-1`: `pv_setpoint_pct_x100` R/W
- `2-3`: `pv_nominal_power_kw_x10` R
- `4`: `pv_enable` R/W

### Input Registers

- `0-1`: `pv_actual_power_kw_x10`
- `2-3`: `pv_available_power_kw_x10`
- `4-5`: `pv_target_power_kw_x10`
- `6`: `pv_enable`

## PCS / BESS Inverter

### Holding Registers

- `0-1`: `pcs_setpoint_pct_x100` R/W
- `2-3`: `pcs_nominal_power_kw_x10` R
- `4`: `pcs_enable` R/W

### Input Registers

- `0-1`: `bess_actual_power_kw_x10`
- `2-3`: `bess_target_power_kw_x10`
- `4`: `pcs_enable`

## Grid Meter

### Holding Registers

- `0-1`: `grid_license_limit_kw_x10` R/W

### Input Registers

- `0-1`: `grid_active_power_kw_x10`
- `2-3`: `grid_license_limit_kw_x10`
- `4`: `grid_limit_exceeded`
- `5`: `grid_direction`

`grid_direction` values:

- `0`: idle
- `1`: export
- `2`: import

## PV Meter

### Input Registers

- `0-1`: `pv_meter_active_power_kw_x10`

## BESS Meter

### Input Registers

- `0-1`: `bess_meter_active_power_kw_x10`

## Simulation Controller

### Holding Registers

- `0-1`: `pyranometer_wm2` R/W
- `2-3`: `local_load_kw_x10` R/W

### Input Registers

- `0-1`: `pyranometer_wm2`
- `2-3`: `local_load_kw_x10`
- `4`: `simulation_status`

`simulation_status` values:

- `1`: running
