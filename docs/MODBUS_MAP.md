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
- Reactive power values: `kVAr x 10`
- Percent values: `% x 100`
- Cos phi values: `x 1000`
- Voltage values: `kV x 100`
- Pyranometer: `W/m2 x 1`
- Enable/status flags: `0` or `1`

## PV Inverter

Configured setpoint holding register base:

- `config.modbus.pv_inverter.setpoint_register_address`
- `config.modbus.pv_inverter.reactive_power_register_address`
- `config.modbus.pv_inverter.cos_phi_register_address`

### Holding Registers

- `A-(A+1)`: `pv_setpoint_pct_x100` R/W
- `A+2-(A+3)`: `pv_nominal_power_kw_x10` R
- `A+4`: `pv_enable` R/W
- `R-(R+1)`: `pv_reactive_power_setpoint_pct_x100` R/W
- `C-(C+1)`: `pv_cos_phi_setpoint_x1000` R/W

Where `A = pv_inverter.setpoint_register_address`
Where `R = pv_inverter.reactive_power_register_address`
Where `C = pv_inverter.cos_phi_register_address`

### Input Registers

- `0-1`: `pv_actual_power_kw_x10`
- `2-3`: `pv_available_power_kw_x10`
- `4-5`: `pv_target_power_kw_x10`
- `6-7`: `pv_actual_reactive_power_kvar_x10`
- `8-9`: `pv_cos_phi_x1000`
- `10-11`: `pv_voltage_kv_x100`
- `12`: `reactive_control_mode`
- `13`: `pv_enable`

## PCS / BESS Inverter

Configured setpoint holding register base:

- `config.modbus.pcs_inverter.setpoint_register_address`

### Holding Registers

- `B-(B+1)`: `pcs_setpoint_kw_x10` R/W
- `B+2-(B+3)`: `pcs_nominal_power_kw_x10` R
- `B+4`: `pcs_enable` R/W

Where `B = pcs_inverter.setpoint_register_address`

### Input Registers

- `0-1`: `bess_actual_power_kw_x10`
- `2-3`: `bess_target_power_kw_x10`
- `4-5`: `bess_reactive_power_kvar_x10`
- `6-7`: `bess_cos_phi_x1000`
- `8-9`: `bess_voltage_kv_x100`
- `10`: `pcs_enable`

## Grid Meter

### Holding Registers

- `0-1`: `grid_license_limit_kw_x10` R/W

### Input Registers

- `0-1`: `grid_active_power_kw_x10`
- `2-3`: `grid_reactive_power_kvar_x10`
- `4-5`: `grid_cos_phi_x1000`
- `6-7`: `grid_voltage_kv_x100`
- `8-9`: `grid_license_limit_kw_x10`
- `10`: `grid_limit_exceeded`
- `11`: `grid_direction`

`grid_direction` values:

- `0`: idle
- `1`: export
- `2`: import

## PV Meter

### Input Registers

- `0-1`: `pv_meter_active_power_kw_x10`
- `2-3`: `pv_meter_reactive_power_kvar_x10`
- `4-5`: `pv_meter_cos_phi_x1000`
- `6-7`: `pv_meter_voltage_kv_x100`

## BESS Meter

### Input Registers

- `0-1`: `bess_meter_active_power_kw_x10`
- `2-3`: `bess_meter_reactive_power_kvar_x10`
- `4-5`: `bess_meter_cos_phi_x1000`
- `6-7`: `bess_meter_voltage_kv_x100`

## Simulation Controller

### Holding Registers

- `0-1`: `pyranometer_wm2` R/W
- `2-3`: `local_load_kw_x10` R/W
- `4`: `reactive_control_mode` R/W
- `5-6`: `voltage_min_kv_x100` R/W
- `7-8`: `voltage_max_kv_x100` R/W

### Input Registers

- `0-1`: `pyranometer_wm2`
- `2-3`: `local_load_kw_x10`
- `4`: `reactive_control_mode`
- `5-6`: `voltage_min_kv_x100`
- `7-8`: `voltage_max_kv_x100`
- `9`: `simulation_status`

`simulation_status` values:

- `1`: running
