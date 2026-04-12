# HMI

The simulator exposes a minimal web HMI when running in `serve` mode.

Default URL:

- `http://127.0.0.1:18080`

## Current Features

- Live view of PV, BESS, Grid, pyranometer, and local load
- Runtime update of:
  - `pv_setpoint_pct`
  - `pcs_setpoint_pct`
  - `pyranometer_wm2`
  - `local_load_kw`
  - `grid_license_limit_kw`
  - `pv_enabled`
  - `bess_enabled`
- Editing Modbus TCP endpoint settings and saving them into `config/simulation.json`

## Important Limitation

Modbus endpoint changes made from the HMI are saved to the config file, but they do not rebind running TCP servers automatically.

After changing Modbus host, port, unit id, or enabled status:

1. Save from the HMI
2. Restart the simulator

## HTTP Endpoints

- `GET /` -> HTML page
- `GET /api/state` -> JSON snapshot of runtime state and Modbus config
- `POST /api/control` -> update runtime values
- `POST /api/config/modbus` -> save Modbus config to JSON
