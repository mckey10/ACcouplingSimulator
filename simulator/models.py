"""Core data models for the AC coupling simulator."""

from __future__ import annotations

from dataclasses import dataclass

from simulator.config import clamp


@dataclass(slots=True)
class SimulationInputs:
    pv_setpoint_pct: float = 0.0
    pcs_setpoint_pct: float = 0.0
    pyranometer_wm2: float = 0.0
    local_load_kw: float = 0.0

    def normalized(self) -> "SimulationInputs":
        return SimulationInputs(
            pv_setpoint_pct=clamp(self.pv_setpoint_pct, 0.0, 100.0),
            pcs_setpoint_pct=clamp(self.pcs_setpoint_pct, -100.0, 100.0),
            pyranometer_wm2=clamp(self.pyranometer_wm2, 0.0, 1500.0),
            local_load_kw=max(0.0, self.local_load_kw),
        )


@dataclass(slots=True)
class InverterState:
    nominal_power_kw: float
    response_time_seconds: float
    enabled: bool = True
    target_power_kw: float = 0.0
    actual_power_kw: float = 0.0


@dataclass(slots=True)
class GridState:
    active_power_kw: float = 0.0
    license_limit_kw: float = 0.0

    @property
    def limit_exceeded(self) -> bool:
        return self.active_power_kw > self.license_limit_kw

    @property
    def direction(self) -> str:
        if self.active_power_kw > 0:
            return "export"
        if self.active_power_kw < 0:
            return "import"
        return "idle"


@dataclass(slots=True)
class SimulationSnapshot:
    pv_target_power_kw: float
    pv_available_power_kw: float
    pv_actual_power_kw: float
    bess_target_power_kw: float
    bess_actual_power_kw: float
    local_load_kw: float
    grid_active_power_kw: float
    pyranometer_wm2: float
