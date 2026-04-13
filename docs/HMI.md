# HMI

The simulator exposes a minimal web HMI when running in `serve` mode.

Default URL:

- `http://127.0.0.1:18080`

## Current Features

- `Operations` page with:
  - live view of PV, BESS, Grid, pyranometer, and local load
  - live view of reactive power, cos phi, and voltage values
  - one shared graph for PV, BESS, and Grid meters
  - top-of-screen grouping by device:
    - `PV Meter`
    - `BESS Meter`
    - `Grid Meter`
    - `Simulation`
  - live alarm indicators for:
    - grid license exceeded
    - grid import active (`Grid < 0`)
  - production-related controls grouped near the live values
- Runtime update of:
  - `pv_setpoint_pct`
  - `pcs_setpoint_kw`
  - `pv_nominal_power_kw`
  - `pcs_nominal_power_kw`
  - `pv_reactive_power_setpoint_pct`
  - `pv_cos_phi_setpoint`
  - `reactive_control_mode`
  - `pyranometer_wm2`
  - `local_load_kw`
  - `voltage_min_kv`
  - `voltage_max_kv`
  - `grid_license_limit_kw`
  - `pv_enabled`
  - `bess_enabled`
- separate `Modbus Config` page for:
  - Modbus TCP endpoint settings
  - setpoint holding register address for `PV inverter` and `PCS inverter`
  - reactive power and cos phi register addresses for `PV inverter`

## Modbus Config Behavior

Modbus endpoint changes made from the HMI are:

1. saved to the config file
2. applied by restarting the Modbus TCP services inside the running process

The HMI itself stays up while Modbus services are rebound.

If a newly entered host or port cannot be bound, the request may fail and the user should correct the config and save again.

This means the `Save Modbus Config` button now applies new Modbus endpoint settings without requiring a full manual restart of the simulator process.

## HTTP Endpoints

- `GET /` -> Operations page
- `GET /modbus` -> Modbus configuration page
- `GET /api/state` -> JSON snapshot of runtime state and Modbus config
- `POST /api/control` -> update runtime values
- `POST /api/config/modbus` -> save Modbus config to JSON
