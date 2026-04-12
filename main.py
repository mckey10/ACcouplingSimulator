"""Entry point for the AC coupling simulator."""

from __future__ import annotations

import argparse
from contextlib import suppress
from pathlib import Path
import threading
import time

from simulator.config import SimulationConfig
from simulator.engine import SimulationEngine
from simulator.hmi import create_hmi_server
from simulator.runtime import SimulationRuntime
from simulator.service_manager import ModbusServiceManager


def build_runtime(config_path: Path) -> tuple[SimulationConfig, SimulationRuntime]:
    config = SimulationConfig.load(config_path)
    runtime = SimulationRuntime(engine=SimulationEngine(config=config))
    return config, runtime


def print_runtime_state(step_number: int, runtime: SimulationRuntime) -> None:
    state = runtime.get_engine_state()
    print(
        f"step={step_number:02d} "
        f"pv_setpoint={state['pv_setpoint_pct']:6.1f}% "
        f"pcs_setpoint={state['pcs_setpoint_pct']:6.1f}% "
        f"pv={state['pv_actual_power_kw']:8.1f}kW "
        f"bess={state['bess_actual_power_kw']:8.1f}kW "
        f"grid={state['grid_active_power_kw']:8.1f}kW "
        f"grid_dir={state['grid_direction']}"
    )


def run_demo(config_path: Path) -> None:
    _, runtime = build_runtime(config_path)
    runtime.update_inputs(pv_setpoint_pct=50.0, pcs_setpoint_pct=0.0)
    for step_number in range(1, 4):
        runtime.step_once()
        print_runtime_state(step_number, runtime)

    runtime.update_inputs(pcs_setpoint_pct=-80.0, pv_setpoint_pct=20.0)
    for step_number in range(4, 7):
        runtime.step_once()
        print_runtime_state(step_number, runtime)

    runtime.update_inputs(local_load_kw=6000.0, pcs_setpoint_pct=50.0, pv_setpoint_pct=30.0)
    for step_number in range(7, 10):
        runtime.step_once()
        print_runtime_state(step_number, runtime)


def run_server(config_path: Path) -> None:
    config, runtime = build_runtime(config_path)
    runtime.start()
    modbus_manager = ModbusServiceManager(runtime=runtime, modbus_config=config.modbus)
    modbus_endpoints = modbus_manager.start()
    hmi_server = create_hmi_server(runtime, config, config_path, modbus_manager=modbus_manager)
    server_threads: list[threading.Thread] = []
    if hmi_server is not None:
        server_threads.append(threading.Thread(target=hmi_server.start, name="hmi-server", daemon=True))
        server_threads[-1].start()

    print("Simulation runtime started.")
    for endpoint in modbus_endpoints:
        print(f"- {endpoint['name']} listening on {endpoint['host']}:{endpoint['port']} unit_id={endpoint['unit_id']}")
    if hmi_server is not None:
        host, port = hmi_server.server.server_address
        print(f"- hmi listening on http://{host}:{port}")

    try:
        while True:
            time.sleep(5.0)
            print_runtime_state(0, runtime)
    except KeyboardInterrupt:
        print("Stopping servers...")
    finally:
        with suppress(Exception):
            modbus_manager.stop()
        if hmi_server is not None:
            with suppress(Exception):
                hmi_server.stop()
        runtime.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AC coupling simulator")
    parser.add_argument("--config", default="config/simulation.json", help="Path to simulation config JSON file.")
    parser.add_argument(
        "--mode",
        choices=("demo", "serve"),
        default="demo",
        help="Run the console demo or start Modbus TCP servers.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config_path = Path(args.config)
    if args.mode == "serve":
        run_server(config_path)
    else:
        run_demo(config_path)
