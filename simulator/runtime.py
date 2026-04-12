"""Thread-safe runtime wrapper around the simulation engine."""

from __future__ import annotations

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
        pcs_setpoint_pct: float | None = None,
        pyranometer_wm2: float | None = None,
        local_load_kw: float | None = None,
    ) -> None:
        with self._lock:
            self.engine.update_inputs(
                pv_setpoint_pct=pv_setpoint_pct,
                pcs_setpoint_pct=pcs_setpoint_pct,
                pyranometer_wm2=pyranometer_wm2,
                local_load_kw=local_load_kw,
            )

    def set_grid_license_limit_kw(self, value: float) -> None:
        with self._lock:
            self.engine.config.grid_license_limit_kw = max(0.0, value)
            self.engine.grid.license_limit_kw = self.engine.config.grid_license_limit_kw

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
                "pcs_setpoint_pct": self.engine.inputs.pcs_setpoint_pct,
                "pyranometer_wm2": self.engine.inputs.pyranometer_wm2,
                "local_load_kw": self.engine.inputs.local_load_kw,
                "pv_enabled": self.engine.pv.enabled,
                "bess_enabled": self.engine.bess.enabled,
                "pv_nominal_power_kw": self.engine.pv.nominal_power_kw,
                "pcs_nominal_power_kw": self.engine.bess.nominal_power_kw,
                "grid_license_limit_kw": self.engine.grid.license_limit_kw,
                "pv_target_power_kw": snapshot.pv_target_power_kw,
                "pv_available_power_kw": snapshot.pv_available_power_kw,
                "pv_actual_power_kw": snapshot.pv_actual_power_kw,
                "bess_target_power_kw": snapshot.bess_target_power_kw,
                "bess_actual_power_kw": snapshot.bess_actual_power_kw,
                "grid_active_power_kw": snapshot.grid_active_power_kw,
                "grid_direction": self.engine.grid.direction,
                "grid_limit_exceeded": self.engine.grid.limit_exceeded,
            }

    def step_once(self) -> SimulationSnapshot:
        with self._lock:
            self._last_snapshot = self.engine.step()
            return self._last_snapshot

    def _run_loop(self) -> None:
        interval = self.engine.config.simulation_step_seconds
        while not self._stop_event.is_set():
            started_at = time.monotonic()
            self.step_once()
            remaining = interval - (time.monotonic() - started_at)
            if remaining > 0:
                self._stop_event.wait(timeout=remaining)
