"""Thread-safe runtime wrapper around the simulation engine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import threading
import time

from simulator.engine import SimulationEngine
from simulator.models import SimulationSnapshot


@dataclass(slots=True)
class SimulationRuntime:
    engine: SimulationEngine
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    _last_snapshot: SimulationSnapshot | None = field(default=None, init=False)
    _history: deque[dict[str, float | int]] = field(default_factory=lambda: deque(maxlen=180), init=False)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="simulation-runtime", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def update_inputs(
        self,
        *,
        pv_setpoint_pct: float | None = None,
        pcs_setpoint_kw: float | None = None,
        pv_reactive_power_setpoint_pct: float | None = None,
        pv_cos_phi_setpoint: float | None = None,
        pyranometer_wm2: float | None = None,
        local_load_kw: float | None = None,
        reactive_control_mode: int | None = None,
        voltage_min_kv: float | None = None,
        voltage_max_kv: float | None = None,
    ) -> None:
        with self._lock:
            self.engine.update_inputs(
                pv_setpoint_pct=pv_setpoint_pct,
                pcs_setpoint_kw=pcs_setpoint_kw,
                pv_reactive_power_setpoint_pct=pv_reactive_power_setpoint_pct,
                pv_cos_phi_setpoint=pv_cos_phi_setpoint,
                pyranometer_wm2=pyranometer_wm2,
                local_load_kw=local_load_kw,
                reactive_control_mode=reactive_control_mode,
                voltage_min_kv=voltage_min_kv,
                voltage_max_kv=voltage_max_kv,
            )

    def set_grid_license_limit_kw(self, value: float) -> None:
        with self._lock:
            self.engine.config.grid_license_limit_kw = max(0.0, value)
            self.engine.grid.license_limit_kw = self.engine.config.grid_license_limit_kw

    def set_nominal_power_kw(self, device: str, value: float) -> None:
        with self._lock:
            sanitized = max(0.0, value)
            if device == "pv":
                self.engine.pv.nominal_power_kw = sanitized
                self.engine.config.pv_inverter.nominal_power_kw = sanitized
            elif device == "bess":
                self.engine.bess.nominal_power_kw = sanitized
                self.engine.config.bess_inverter.nominal_power_kw = sanitized
            else:
                raise ValueError(f"unknown device {device}")

    def set_device_enabled(self, device: str, enabled: bool) -> None:
        with self._lock:
            if device == "pv":
                self.engine.pv.enabled = enabled
            elif device == "bess":
                self.engine.bess.enabled = enabled
            else:
                raise ValueError(f"unknown device {device}")

    def is_device_enabled(self, device: str) -> bool:
        with self._lock:
            if device == "pv":
                return self.engine.pv.enabled
            if device == "bess":
                return self.engine.bess.enabled
            raise ValueError(f"unknown device {device}")

    def get_snapshot(self) -> SimulationSnapshot:
        with self._lock:
            if self._last_snapshot is None:
                self._last_snapshot = self.engine.step()
            return self._last_snapshot

    def get_engine_state(self) -> dict[str, float | str | bool]:
        with self._lock:
            snapshot = self._last_snapshot or self.engine.step()
            self._last_snapshot = snapshot
            return {
                "pv_setpoint_pct": self.engine.inputs.pv_setpoint_pct,
                "pcs_setpoint_kw": self.engine.inputs.pcs_setpoint_kw,
                "pv_reactive_power_setpoint_pct": self.engine.inputs.pv_reactive_power_setpoint_pct,
                "pv_cos_phi_setpoint": self.engine.inputs.pv_cos_phi_setpoint,
                "pyranometer_wm2": self.engine.inputs.pyranometer_wm2,
                "local_load_kw": self.engine.inputs.local_load_kw,
                "reactive_control_mode": self.engine.inputs.reactive_control_mode,
                "voltage_min_kv": self.engine.inputs.voltage_min_kv,
                "voltage_max_kv": self.engine.inputs.voltage_max_kv,
                "pv_enabled": self.engine.pv.enabled,
                "bess_enabled": self.engine.bess.enabled,
                "pv_nominal_power_kw": self.engine.pv.nominal_power_kw,
                "pcs_nominal_power_kw": self.engine.bess.nominal_power_kw,
                "grid_license_limit_kw": self.engine.grid.license_limit_kw,
                "pv_target_power_kw": snapshot.pv_target_power_kw,
                "pv_available_power_kw": snapshot.pv_available_power_kw,
                "pv_actual_power_kw": snapshot.pv_actual_power_kw,
                "pv_target_reactive_power_kvar": snapshot.pv_target_reactive_power_kvar,
                "pv_actual_reactive_power_kvar": snapshot.pv_actual_reactive_power_kvar,
                "pv_cos_phi": snapshot.pv_cos_phi,
                "pv_voltage_kv": snapshot.pv_voltage_kv,
                "bess_target_power_kw": snapshot.bess_target_power_kw,
                "bess_actual_power_kw": snapshot.bess_actual_power_kw,
                "bess_reactive_power_kvar": snapshot.bess_reactive_power_kvar,
                "bess_cos_phi": snapshot.bess_cos_phi,
                "bess_voltage_kv": snapshot.bess_voltage_kv,
                "grid_active_power_kw": snapshot.grid_active_power_kw,
                "grid_reactive_power_kvar": snapshot.grid_reactive_power_kvar,
                "grid_cos_phi": snapshot.grid_cos_phi,
                "grid_voltage_kv": snapshot.grid_voltage_kv,
                "grid_direction": self.engine.grid.direction,
                "grid_limit_exceeded": self.engine.grid.limit_exceeded,
            }

    def get_history(self) -> list[dict[str, float | int]]:
        with self._lock:
            return list(self._history)

    def step_once(self) -> SimulationSnapshot:
        with self._lock:
            self._last_snapshot = self.engine.step()
            self._history.append(
                {
                    "timestamp": int(time.time()),
                    "pv_power_kw": self._last_snapshot.pv_actual_power_kw,
                    "pv_reactive_power_kvar": self._last_snapshot.pv_actual_reactive_power_kvar,
                    "bess_power_kw": self._last_snapshot.bess_actual_power_kw,
                    "bess_reactive_power_kvar": self._last_snapshot.bess_reactive_power_kvar,
                    "grid_power_kw": self._last_snapshot.grid_active_power_kw,
                    "grid_reactive_power_kvar": self._last_snapshot.grid_reactive_power_kvar,
                }
            )
            return self._last_snapshot

    def _run_loop(self) -> None:
        interval = self.engine.config.simulation_step_seconds
        while not self._stop_event.is_set():
            started_at = time.monotonic()
            self.step_once()
            remaining = interval - (time.monotonic() - started_at)
            if remaining > 0:
                self._stop_event.wait(timeout=remaining)
