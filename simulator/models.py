"""Core data models for the AC coupling simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from simulator.config import clamp


@dataclass(slots=True)
class SimulationInputs:
    pv_setpoint_pct: float = 0.0
    pcs_setpoint_pct: float = 0.0
    pv_reactive_power_setpoint_pct: float = 0.0
    pv_cos_phi_setpoint: float = 1.0
    pyranometer_wm2: float = 0.0
    local_load_kw: float = 0.0
    reactive_control_mode: int = 0
    voltage_min_kv: float = 20.0
    voltage_max_kv: float = 24.0

    def normalized(self) -> "SimulationInputs":
        voltage_min_kv = min(self.voltage_min_kv, self.voltage_max_kv)
        voltage_max_kv = max(self.voltage_min_kv, self.voltage_max_kv)
        return SimulationInputs(
            pv_setpoint_pct=clamp(self.pv_setpoint_pct, 0.0, 100.0),
            pcs_setpoint_pct=clamp(self.pcs_setpoint_pct, -100.0, 100.0),
            pv_reactive_power_setpoint_pct=clamp(self.pv_reactive_power_setpoint_pct, -100.0, 100.0),
            pv_cos_phi_setpoint=clamp(self.pv_cos_phi_setpoint, -1.0, 1.0),
            pyranometer_wm2=clamp(self.pyranometer_wm2, 0.0, 1500.0),
            local_load_kw=max(0.0, self.local_load_kw),
            reactive_control_mode=0 if self.reactive_control_mode == 0 else 1,
            voltage_min_kv=voltage_min_kv,
            voltage_max_kv=voltage_max_kv,
        )


@dataclass(slots=True)
class InverterState:
    nominal_power_kw: float
    response_time_seconds: float
    enabled: bool = True
    target_power_kw: float = 0.0
    actual_power_kw: float = 0.0
    target_reactive_power_kvar: float = 0.0
    actual_reactive_power_kvar: float = 0.0
    cos_phi: float = 1.0
    voltage_kv: float = 22.0


@dataclass(slots=True)
class GridState:
    active_power_kw: float = 0.0
    reactive_power_kvar: float = 0.0
    license_limit_kw: float = 0.0
    cos_phi: float = 1.0
    voltage_kv: float = 22.0

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
    pv_target_reactive_power_kvar: float
    pv_actual_reactive_power_kvar: float
    pv_cos_phi: float
    pv_voltage_kv: float
    bess_target_power_kw: float
    bess_actual_power_kw: float
    bess_reactive_power_kvar: float
    bess_cos_phi: float
    bess_voltage_kv: float
    local_load_kw: float
    grid_active_power_kw: float
    grid_reactive_power_kvar: float
    grid_cos_phi: float
    grid_voltage_kv: float
    pyranometer_wm2: float
    reactive_control_mode: int
