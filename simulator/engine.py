"""Simulation engine for the AC coupling model."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp

from simulator.config import SimulationConfig
from simulator.models import GridState, InverterState, SimulationInputs, SimulationSnapshot


def first_order_response(current: float, target: float, dt_seconds: float, response_time_seconds: float) -> float:
    """Move the current value toward the target using a first-order response."""
    alpha = 1.0 - exp(-dt_seconds / response_time_seconds)
    return current + (target - current) * alpha


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
        )

    def update_inputs(
        self,
        *,
        pv_setpoint_pct: float | None = None,
        pcs_setpoint_pct: float | None = None,
        pyranometer_wm2: float | None = None,
        local_load_kw: float | None = None,
    ) -> None:
        if pv_setpoint_pct is not None:
            self.inputs.pv_setpoint_pct = pv_setpoint_pct
        if pcs_setpoint_pct is not None:
            self.inputs.pcs_setpoint_pct = pcs_setpoint_pct
        if pyranometer_wm2 is not None:
            self.inputs.pyranometer_wm2 = pyranometer_wm2
        if local_load_kw is not None:
            self.inputs.local_load_kw = local_load_kw
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

        bess_target_power_kw = self.bess.nominal_power_kw * inputs.pcs_setpoint_pct / 100.0
        if not self.bess.enabled:
            bess_target_power_kw = 0.0

        self.pv.target_power_kw = pv_target_power_kw
        self.bess.target_power_kw = bess_target_power_kw

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

        self.grid.active_power_kw = self.pv.actual_power_kw + self.bess.actual_power_kw - inputs.local_load_kw

        return SimulationSnapshot(
            pv_target_power_kw=self.pv.target_power_kw,
            pv_available_power_kw=pv_available_power_kw,
            pv_actual_power_kw=self.pv.actual_power_kw,
            bess_target_power_kw=self.bess.target_power_kw,
            bess_actual_power_kw=self.bess.actual_power_kw,
            local_load_kw=inputs.local_load_kw,
            grid_active_power_kw=self.grid.active_power_kw,
            pyranometer_wm2=inputs.pyranometer_wm2,
        )
