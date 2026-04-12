# ACcouplingSimulator

Python project for experimenting with and simulating AC coupling behavior.

## Current state

The repository is initialized and connected to GitHub. The project currently contains a starter `main.py` file created from the PyCharm template.

The working simulation specification is stored in [docs/SIMULATION_SPEC.md](/C:/Users/Galtech/PycharmProjects/ACcouplingSimulator/docs/SIMULATION_SPEC.md).
The implemented Modbus register map is stored in [docs/MODBUS_MAP.md](/C:/Users/Galtech/PycharmProjects/ACcouplingSimulator/docs/MODBUS_MAP.md).
The current HMI behavior is described in [docs/HMI.md](/C:/Users/Galtech/PycharmProjects/ACcouplingSimulator/docs/HMI.md).

The first implementation stage now includes:

- a simulation engine in `simulator/engine.py`
- configuration loading in `simulator/config.py`
- core data models in `simulator/models.py`
- a minimal Modbus TCP layer in `simulator/modbus.py`
- a minimal web HMI in `simulator/hmi.py`
- a thread-safe runtime wrapper in `simulator/runtime.py`
- a sample configuration file in `config/simulation.json`
- a demo entry point in `main.py`

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

- Replace the template code in `main.py` with the actual simulator logic.
- Add dependencies to `requirements.txt` or `pyproject.toml` when they are known.
- Create the first commit and push it to GitHub.
