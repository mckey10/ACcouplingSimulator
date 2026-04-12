# HMI

The simulator exposes a minimal web HMI when running in `serve` mode.

Default URL:

- `http://127.0.0.1:18080`

## Current Features

- `Operations` page with:
  - live view of PV, BESS, Grid, pyranometer, and local load
  - one shared graph for PV, BESS, and Grid meters
  - production-related controls grouped near the live values
- Runtime update of:
  - `pv_setpoint_pct`
  - `pcs_setpoint_pct`
  - `pv_nominal_power_kw`
  - `pcs_nominal_power_kw`
  - `pyranometer_wm2`
  - `local_load_kw`
  - `grid_license_limit_kw`
  - `pv_enabled`
  - `bess_enabled`
- separate `Modbus Config` page for:
  - Modbus TCP endpoint settings
  - setpoint holding register address for `PV inverter` and `PCS inverter`

## Important Limitation

Modbus endpoint changes made from the HMI are saved to the config file, but they do not rebind running TCP servers automatically.

After changing Modbus host, port, unit id, enabled status, or setpoint register address:

1. Save from the HMI
2. Restart the simulator

## HTTP Endpoints

- `GET /` -> Operations page
- `GET /modbus` -> Modbus configuration page
- `GET /api/state` -> JSON snapshot of runtime state and Modbus config
- `POST /api/control` -> update runtime values
- `POST /api/config/modbus` -> save Modbus config to JSON
