# ACcouplingSimulator

Python project for experimenting with and simulating AC coupling behavior.

## Current state

The repository is initialized and connected to GitHub.

The working simulation specification is stored in [docs/SIMULATION_SPEC.md](/C:/Users/Galtech/PycharmProjects/ACcouplingSimulator/docs/SIMULATION_SPEC.md).
The implemented Modbus register map is stored in [docs/MODBUS_MAP.md](/C:/Users/Galtech/PycharmProjects/ACcouplingSimulator/docs/MODBUS_MAP.md).
The current HMI behavior is described in [docs/HMI.md](/C:/Users/Galtech/PycharmProjects/ACcouplingSimulator/docs/HMI.md).

The first implementation stage now includes:

- a simulation engine in `simulator/engine.py`
- configuration loading in `simulator/config.py`
- core data models in `simulator/models.py`
- a minimal Modbus TCP layer in `simulator/modbus.py`
- a Modbus lifecycle manager in `simulator/service_manager.py`
- a minimal web HMI in `simulator/hmi.py`
- a thread-safe runtime wrapper in `simulator/runtime.py`
- a sample configuration file in `config/simulation.json`
- a demo entry point in `main.py`

The current implementation already supports:

- real-time simulation of PV, PCS / BESS, Grid, and local load
- reactive power, cos phi, and voltage behavior for PV and meters
- Modbus TCP endpoints for logical devices
- a web HMI with:
  - operations dashboard
  - top summary grouped by PV, BESS, Grid, and Simulation
  - live graph for PV, BESS, and Grid
  - live alarms for grid license exceed and grid import
  - runtime editing of active/reactive setpoints, nominal powers, voltage limits, pyranometer, load, and enable states
  - a separate Modbus configuration page
  - automatic Modbus service restart after `Save Modbus Config`

## Run

```bash
python main.py
```

This currently runs a console demo with a few scenario changes and prints the simulated PV, BESS, load, and grid power values for each step.

To start the Modbus TCP servers instead:

```bash
python main.py --mode serve
```

In `serve` mode the web HMI also starts by default on `http://127.0.0.1:18080`.

## Next steps

- Add dependencies to `requirements.txt` or `pyproject.toml` when they are known.
- Add automated tests for simulation math, Modbus register behavior, and HMI endpoints.
- Extend the model with optional SOC / energy counters when needed.
