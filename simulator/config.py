"""Configuration loading for the AC coupling simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a floating-point value into the provided inclusive range."""
    return max(minimum, min(value, maximum))


@dataclass(slots=True)
class InverterConfig:
    nominal_power_kw: float
    response_time_seconds: float = 2.0
    enabled: bool = True

    def sanitized_nominal_power_kw(self) -> float:
        return max(0.0, self.nominal_power_kw)

    def sanitized_response_time_seconds(self) -> float:
        return max(0.1, self.response_time_seconds)


@dataclass(slots=True)
class ModbusDeviceConfig:
    host: str = "127.0.0.1"
    port: int = 15000
    unit_id: int = 1
    enabled: bool = True
    setpoint_register_address: int = 0
    reactive_power_register_address: int = 20
    cos_phi_register_address: int = 40


@dataclass(slots=True)
class ModbusConfig:
    pv_inverter: ModbusDeviceConfig = field(default_factory=lambda: ModbusDeviceConfig(port=15001, unit_id=1))
    pcs_inverter: ModbusDeviceConfig = field(default_factory=lambda: ModbusDeviceConfig(port=15002, unit_id=2))
    grid_meter: ModbusDeviceConfig = field(default_factory=lambda: ModbusDeviceConfig(port=15003, unit_id=3))
    pv_meter: ModbusDeviceConfig = field(default_factory=lambda: ModbusDeviceConfig(port=15004, unit_id=4))
    bess_meter: ModbusDeviceConfig = field(default_factory=lambda: ModbusDeviceConfig(port=15005, unit_id=5))
    simulation_controller: ModbusDeviceConfig = field(
        default_factory=lambda: ModbusDeviceConfig(port=15010, unit_id=10)
    )


@dataclass(slots=True)
class HmiConfig:
    host: str = "127.0.0.1"
    port: int = 18080
    enabled: bool = True


def parse_modbus_device(raw: dict, default_port: int, default_unit_id: int) -> ModbusDeviceConfig:
    return ModbusDeviceConfig(
        host=raw.get("host", "127.0.0.1"),
        port=int(raw.get("port", default_port)),
        unit_id=int(raw.get("unit_id", default_unit_id)),
        enabled=bool(raw.get("enabled", True)),
        setpoint_register_address=max(0, int(raw.get("setpoint_register_address", 0))),
        reactive_power_register_address=max(0, int(raw.get("reactive_power_register_address", 20))),
        cos_phi_register_address=max(0, int(raw.get("cos_phi_register_address", 40))),
    )


@dataclass(slots=True)
class SimulationConfig:
    pv_inverter: InverterConfig
    bess_inverter: InverterConfig
    grid_license_limit_kw: float
    pyranometer_wm2: float
    local_load_kw: float
    reactive_control_mode: int = 0
    voltage_min_kv: float = 20.0
    voltage_max_kv: float = 24.0
    simulation_step_seconds: float = 1.0
    modbus: ModbusConfig = field(default_factory=ModbusConfig)
    hmi: HmiConfig = field(default_factory=HmiConfig)

    @classmethod
    def from_dict(cls, raw: dict) -> "SimulationConfig":
        pv_inverter = InverterConfig(**raw["pv_inverter"])
        bess_inverter = InverterConfig(**raw["bess_inverter"])
        modbus_raw = raw.get("modbus", {})
        hmi_raw = raw.get("hmi", {})
        return cls(
            pv_inverter=pv_inverter,
            bess_inverter=bess_inverter,
            grid_license_limit_kw=max(0.0, raw.get("grid_license_limit_kw", 0.0)),
            pyranometer_wm2=clamp(float(raw.get("pyranometer_wm2", 0.0)), 0.0, 1500.0),
            local_load_kw=max(0.0, float(raw.get("local_load_kw", 0.0))),
            reactive_control_mode=0 if int(raw.get("reactive_control_mode", 0)) == 0 else 1,
            voltage_min_kv=float(raw.get("voltage_min_kv", 20.0)),
            voltage_max_kv=float(raw.get("voltage_max_kv", 24.0)),
            simulation_step_seconds=max(0.1, float(raw.get("simulation_step_seconds", 1.0))),
            modbus=ModbusConfig(
                pv_inverter=parse_modbus_device(modbus_raw.get("pv_inverter", {}), 15001, 1),
                pcs_inverter=parse_modbus_device(modbus_raw.get("pcs_inverter", {}), 15002, 2),
                grid_meter=parse_modbus_device(modbus_raw.get("grid_meter", {}), 15003, 3),
                pv_meter=parse_modbus_device(modbus_raw.get("pv_meter", {}), 15004, 4),
                bess_meter=parse_modbus_device(modbus_raw.get("bess_meter", {}), 15005, 5),
                simulation_controller=parse_modbus_device(modbus_raw.get("simulation_controller", {}), 15010, 10),
            ),
            hmi=HmiConfig(
                host=hmi_raw.get("host", "127.0.0.1"),
                port=int(hmi_raw.get("port", 18080)),
                enabled=bool(hmi_raw.get("enabled", True)),
            ),
        )

    @classmethod
    def load(cls, path: Path) -> "SimulationConfig":
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return cls.from_dict(raw)

    def to_dict(self) -> dict:
        return {
            "pv_inverter": {
                "nominal_power_kw": self.pv_inverter.nominal_power_kw,
                "response_time_seconds": self.pv_inverter.response_time_seconds,
                "enabled": self.pv_inverter.enabled,
            },
            "bess_inverter": {
                "nominal_power_kw": self.bess_inverter.nominal_power_kw,
                "response_time_seconds": self.bess_inverter.response_time_seconds,
                "enabled": self.bess_inverter.enabled,
            },
            "grid_license_limit_kw": self.grid_license_limit_kw,
            "pyranometer_wm2": self.pyranometer_wm2,
            "local_load_kw": self.local_load_kw,
            "reactive_control_mode": self.reactive_control_mode,
            "voltage_min_kv": self.voltage_min_kv,
            "voltage_max_kv": self.voltage_max_kv,
            "simulation_step_seconds": self.simulation_step_seconds,
            "modbus": {
                "pv_inverter": self._modbus_device_to_dict(self.modbus.pv_inverter),
                "pcs_inverter": self._modbus_device_to_dict(self.modbus.pcs_inverter),
                "grid_meter": self._modbus_device_to_dict(self.modbus.grid_meter),
                "pv_meter": self._modbus_device_to_dict(self.modbus.pv_meter),
                "bess_meter": self._modbus_device_to_dict(self.modbus.bess_meter),
                "simulation_controller": self._modbus_device_to_dict(self.modbus.simulation_controller),
            },
            "hmi": {
                "host": self.hmi.host,
                "port": self.hmi.port,
                "enabled": self.hmi.enabled,
            },
        }

    def save(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
            handle.write("\n")

    @staticmethod
    def _modbus_device_to_dict(device: ModbusDeviceConfig) -> dict:
        return {
            "host": device.host,
            "port": device.port,
            "unit_id": device.unit_id,
            "enabled": device.enabled,
            "setpoint_register_address": device.setpoint_register_address,
            "reactive_power_register_address": device.reactive_power_register_address,
            "cos_phi_register_address": device.cos_phi_register_address,
        }
