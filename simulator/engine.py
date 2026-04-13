"""Simulation engine for the AC coupling model."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, sqrt

from simulator.config import SimulationConfig
from simulator.models import GridState, InverterState, SimulationInputs, SimulationSnapshot


def first_order_response(current: float, target: float, dt_seconds: float, response_time_seconds: float) -> float:
    """Move the current value toward the target using a first-order response."""
    alpha = 1.0 - exp(-dt_seconds / response_time_seconds)
    return current + (target - current) * alpha


def power_factor_from_p_q(active_power_kw: float, reactive_power_kvar: float) -> float:
    if abs(active_power_kw) < 1e-6 or abs(reactive_power_kvar) < 1e-6:
        return 1.0
    apparent_power = sqrt(active_power_kw**2 + reactive_power_kvar**2)
    return abs(active_power_kw) / apparent_power * (1.0 if reactive_power_kvar >= 0 else -1.0)


def reactive_power_from_cos_phi(active_power_kw: float, cos_phi: float) -> float:
    if abs(active_power_kw) < 1e-6:
        return 0.0
    limited = max(0.01, min(1.0, abs(cos_phi)))
    apparent_power = abs(active_power_kw) / limited
    reactive_magnitude = sqrt(max(0.0, apparent_power**2 - active_power_kw**2))
    return reactive_magnitude if cos_phi >= 0 else -reactive_magnitude


def voltage_from_q_pct(q_pct: float, voltage_min_kv: float, voltage_max_kv: float) -> float:
    q_pct = max(-100.0, min(100.0, q_pct))
    voltage_base = (voltage_min_kv + voltage_max_kv) / 2.0
    half_range = (voltage_max_kv - voltage_min_kv) / 2.0
    voltage = voltage_base - (q_pct / 100.0) * half_range
    return max(voltage_min_kv, min(voltage_max_kv, voltage))


@dataclass(slots=True)
class SimulationEngine:
    config: SimulationConfig
    pv: InverterState = field(init=False)
    bess: InverterState = field(init=False)
    grid: GridState = field(init=False)
    inputs: SimulationInputs = field(init=False)

    def __post_init__(self) -> None:
        self.pv = InverterState(
            nominal_power_kw=self.config.pv_inverter.sanitized_nominal_power_kw(),
            response_time_seconds=self.config.pv_inverter.sanitized_response_time_seconds(),
            enabled=self.config.pv_inverter.enabled,
        )
        self.bess = InverterState(
            nominal_power_kw=self.config.bess_inverter.sanitized_nominal_power_kw(),
            response_time_seconds=self.config.bess_inverter.sanitized_response_time_seconds(),
            enabled=self.config.bess_inverter.enabled,
        )
        self.grid = GridState(license_limit_kw=self.config.grid_license_limit_kw)
        self.inputs = SimulationInputs(
            pyranometer_wm2=self.config.pyranometer_wm2,
            local_load_kw=self.config.local_load_kw,
            reactive_control_mode=self.config.reactive_control_mode,
            voltage_min_kv=self.config.voltage_min_kv,
            voltage_max_kv=self.config.voltage_max_kv,
        )
        base_voltage = (self.inputs.voltage_min_kv + self.inputs.voltage_max_kv) / 2.0
        self.pv.voltage_kv = base_voltage
        self.bess.voltage_kv = base_voltage
        self.grid.voltage_kv = base_voltage

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
        if pv_setpoint_pct is not None:
            self.inputs.pv_setpoint_pct = pv_setpoint_pct
        if pcs_setpoint_kw is not None:
            self.inputs.pcs_setpoint_kw = max(-self.bess.nominal_power_kw, min(self.bess.nominal_power_kw, pcs_setpoint_kw))
        if pv_reactive_power_setpoint_pct is not None:
            self.inputs.pv_reactive_power_setpoint_pct = pv_reactive_power_setpoint_pct
        if pv_cos_phi_setpoint is not None:
            self.inputs.pv_cos_phi_setpoint = pv_cos_phi_setpoint
        if pyranometer_wm2 is not None:
            self.inputs.pyranometer_wm2 = pyranometer_wm2
        if local_load_kw is not None:
            self.inputs.local_load_kw = local_load_kw
        if reactive_control_mode is not None:
            self.inputs.reactive_control_mode = reactive_control_mode
        if voltage_min_kv is not None:
            self.inputs.voltage_min_kv = voltage_min_kv
        if voltage_max_kv is not None:
            self.inputs.voltage_max_kv = voltage_max_kv
        self.inputs = self.inputs.normalized()

    def step(self) -> SimulationSnapshot:
        inputs = self.inputs.normalized()
        self.inputs = inputs
        step_seconds = self.config.simulation_step_seconds

        pv_available_power_kw = self.pv.nominal_power_kw * inputs.pyranometer_wm2 / 1500.0
        pv_target_power_kw = self.pv.nominal_power_kw * inputs.pv_setpoint_pct / 100.0
        pv_target_power_kw = min(pv_target_power_kw, pv_available_power_kw)
        if not self.pv.enabled:
            pv_target_power_kw = 0.0

        bess_target_power_kw = max(-self.bess.nominal_power_kw, min(self.bess.nominal_power_kw, inputs.pcs_setpoint_kw))
        if not self.bess.enabled:
            bess_target_power_kw = 0.0

        pv_reactive_target_by_q_kvar = self.pv.nominal_power_kw * inputs.pv_reactive_power_setpoint_pct / 100.0
        pv_reactive_target_by_cos_phi_kvar = reactive_power_from_cos_phi(
            active_power_kw=self.pv.actual_power_kw if abs(self.pv.actual_power_kw) > 1e-6 else pv_target_power_kw,
            cos_phi=inputs.pv_cos_phi_setpoint,
        )
        pv_target_reactive_power_kvar = (
            pv_reactive_target_by_q_kvar if inputs.reactive_control_mode == 0 else pv_reactive_target_by_cos_phi_kvar
        )
        if not self.pv.enabled:
            pv_target_reactive_power_kvar = 0.0

        self.pv.target_power_kw = pv_target_power_kw
        self.bess.target_power_kw = bess_target_power_kw
        self.pv.target_reactive_power_kvar = pv_target_reactive_power_kvar

        self.pv.actual_power_kw = first_order_response(
            current=self.pv.actual_power_kw,
            target=self.pv.target_power_kw,
            dt_seconds=step_seconds,
            response_time_seconds=self.pv.response_time_seconds,
        )
        self.bess.actual_power_kw = first_order_response(
            current=self.bess.actual_power_kw,
            target=self.bess.target_power_kw,
            dt_seconds=step_seconds,
            response_time_seconds=self.bess.response_time_seconds,
        )
        self.pv.actual_reactive_power_kvar = first_order_response(
            current=self.pv.actual_reactive_power_kvar,
            target=self.pv.target_reactive_power_kvar,
            dt_seconds=step_seconds,
            response_time_seconds=self.pv.response_time_seconds,
        )

        self.grid.active_power_kw = self.pv.actual_power_kw + self.bess.actual_power_kw - inputs.local_load_kw
        self.grid.reactive_power_kvar = self.pv.actual_reactive_power_kvar

        self.pv.cos_phi = power_factor_from_p_q(self.pv.actual_power_kw, self.pv.actual_reactive_power_kvar)
        self.bess.cos_phi = 1.0
        self.grid.cos_phi = power_factor_from_p_q(self.grid.active_power_kw, self.grid.reactive_power_kvar)

        pv_q_pct = 0.0 if self.pv.nominal_power_kw <= 0 else self.pv.actual_reactive_power_kvar / self.pv.nominal_power_kw * 100.0
        grid_q_pct = 0.0 if self.pv.nominal_power_kw <= 0 else self.grid.reactive_power_kvar / self.pv.nominal_power_kw * 100.0
        voltage_base = (inputs.voltage_min_kv + inputs.voltage_max_kv) / 2.0
        self.pv.voltage_kv = voltage_from_q_pct(pv_q_pct, inputs.voltage_min_kv, inputs.voltage_max_kv)
        self.bess.voltage_kv = voltage_base
        self.grid.voltage_kv = voltage_from_q_pct(grid_q_pct, inputs.voltage_min_kv, inputs.voltage_max_kv)

        return SimulationSnapshot(
            pv_target_power_kw=self.pv.target_power_kw,
            pv_available_power_kw=pv_available_power_kw,
            pv_actual_power_kw=self.pv.actual_power_kw,
            pv_target_reactive_power_kvar=self.pv.target_reactive_power_kvar,
            pv_actual_reactive_power_kvar=self.pv.actual_reactive_power_kvar,
            pv_cos_phi=self.pv.cos_phi,
            pv_voltage_kv=self.pv.voltage_kv,
            bess_target_power_kw=self.bess.target_power_kw,
            bess_actual_power_kw=self.bess.actual_power_kw,
            bess_reactive_power_kvar=0.0,
            bess_cos_phi=self.bess.cos_phi,
            bess_voltage_kv=self.bess.voltage_kv,
            local_load_kw=inputs.local_load_kw,
            grid_active_power_kw=self.grid.active_power_kw,
            grid_reactive_power_kvar=self.grid.reactive_power_kvar,
            grid_cos_phi=self.grid.cos_phi,
            grid_voltage_kv=self.grid.voltage_kv,
            pyranometer_wm2=inputs.pyranometer_wm2,
            reactive_control_mode=inputs.reactive_control_mode,
        )
