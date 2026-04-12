"""Minimal Modbus TCP implementation for the simulator."""

from __future__ import annotations

from dataclasses import dataclass
import socketserver
import struct
from typing import Callable

from simulator.config import ModbusConfig, ModbusDeviceConfig
from simulator.runtime import SimulationRuntime

READ_HOLDING_REGISTERS = 3
READ_INPUT_REGISTERS = 4
WRITE_SINGLE_REGISTER = 6
WRITE_MULTIPLE_REGISTERS = 16


def clamp_register(value: int) -> int:
    return value & 0xFFFF


def encode_int32_words(value: int) -> list[int]:
    packed = struct.pack(">i", value)
    high, low = struct.unpack(">HH", packed)
    return [high, low]


def decode_int32_words(words: list[int]) -> int:
    packed = struct.pack(">HH", words[0], words[1])
    return struct.unpack(">i", packed)[0]


def scale_to_words(value: float, scale: float = 10.0) -> list[int]:
    return encode_int32_words(int(round(value * scale)))


def words_to_scaled_value(words: list[int], scale: float = 10.0) -> float:
    return decode_int32_words(words) / scale


@dataclass(slots=True)
class RegisterValue:
    address: int
    width: int
    reader: Callable[[], list[int]]
    writer: Callable[[list[int]], None] | None = None


class DeviceRegisterMap:
    def __init__(self) -> None:
        self.holding: dict[int, RegisterValue] = {}
        self.input_registers: dict[int, RegisterValue] = {}

    def add_holding(
        self,
        address: int,
        width: int,
        reader: Callable[[], list[int]],
        writer: Callable[[list[int]], None] | None = None,
    ) -> None:
        self.holding[address] = RegisterValue(address=address, width=width, reader=reader, writer=writer)

    def add_input(self, address: int, width: int, reader: Callable[[], list[int]]) -> None:
        self.input_registers[address] = RegisterValue(address=address, width=width, reader=reader)

    def read(self, space: str, address: int, quantity: int) -> list[int]:
        registers = self.holding if space == "holding" else self.input_registers
        result: list[int] = []
        cursor = address
        end = address + quantity
        while cursor < end:
            entry = registers.get(cursor)
            if entry is None:
                raise KeyError(cursor)
            words = entry.reader()
            if len(words) != entry.width:
                raise ValueError(f"register width mismatch at {cursor}")
            result.extend(clamp_register(word) for word in words)
            cursor += entry.width
        return result

    def write(self, address: int, values: list[int]) -> None:
        cursor = address
        offset = 0
        end = address + len(values)
        while cursor < end:
            entry = self.holding.get(cursor)
            if entry is None or entry.writer is None:
                raise KeyError(cursor)
            chunk = values[offset : offset + entry.width]
            if len(chunk) != entry.width:
                raise ValueError(f"incomplete write at {cursor}")
            entry.writer(chunk)
            cursor += entry.width
            offset += entry.width


def build_register_maps(runtime: SimulationRuntime) -> dict[str, DeviceRegisterMap]:
    maps = {
        "pv_inverter": DeviceRegisterMap(),
        "pcs_inverter": DeviceRegisterMap(),
        "grid_meter": DeviceRegisterMap(),
        "pv_meter": DeviceRegisterMap(),
        "bess_meter": DeviceRegisterMap(),
        "simulation_controller": DeviceRegisterMap(),
    }

    pv = maps["pv_inverter"]
    pv.add_holding(0, 2, lambda: scale_to_words(runtime.get_engine_state()["pv_setpoint_pct"], 100.0), lambda words: runtime.update_inputs(pv_setpoint_pct=words_to_scaled_value(words, 100.0)))
    pv.add_holding(2, 2, lambda: scale_to_words(runtime.get_engine_state()["pv_nominal_power_kw"]))
    pv.add_holding(4, 1, lambda: [1 if runtime.is_device_enabled("pv") else 0], lambda words: runtime.set_device_enabled("pv", bool(words[0])))
    pv.add_input(0, 2, lambda: scale_to_words(runtime.get_engine_state()["pv_actual_power_kw"]))
    pv.add_input(2, 2, lambda: scale_to_words(runtime.get_engine_state()["pv_available_power_kw"]))
    pv.add_input(4, 2, lambda: scale_to_words(runtime.get_engine_state()["pv_target_power_kw"]))
    pv.add_input(6, 1, lambda: [1 if runtime.is_device_enabled("pv") else 0])

    pcs = maps["pcs_inverter"]
    pcs.add_holding(0, 2, lambda: scale_to_words(runtime.get_engine_state()["pcs_setpoint_pct"], 100.0), lambda words: runtime.update_inputs(pcs_setpoint_pct=words_to_scaled_value(words, 100.0)))
    pcs.add_holding(2, 2, lambda: scale_to_words(runtime.get_engine_state()["pcs_nominal_power_kw"]))
    pcs.add_holding(4, 1, lambda: [1 if runtime.is_device_enabled("bess") else 0], lambda words: runtime.set_device_enabled("bess", bool(words[0])))
    pcs.add_input(0, 2, lambda: scale_to_words(runtime.get_engine_state()["bess_actual_power_kw"]))
    pcs.add_input(2, 2, lambda: scale_to_words(runtime.get_engine_state()["bess_target_power_kw"]))
    pcs.add_input(4, 1, lambda: [1 if runtime.is_device_enabled("bess") else 0])

    grid = maps["grid_meter"]
    grid.add_holding(0, 2, lambda: scale_to_words(runtime.get_engine_state()["grid_license_limit_kw"]), lambda words: runtime.set_grid_license_limit_kw(words_to_scaled_value(words)))
    grid.add_input(0, 2, lambda: scale_to_words(runtime.get_engine_state()["grid_active_power_kw"]))
    grid.add_input(2, 2, lambda: scale_to_words(runtime.get_engine_state()["grid_license_limit_kw"]))
    grid.add_input(4, 1, lambda: [1 if runtime.get_engine_state()["grid_limit_exceeded"] else 0])
    grid.add_input(5, 1, lambda: [0 if runtime.get_engine_state()["grid_direction"] == "idle" else 1 if runtime.get_engine_state()["grid_direction"] == "export" else 2])

    pv_meter = maps["pv_meter"]
    pv_meter.add_input(0, 2, lambda: scale_to_words(runtime.get_engine_state()["pv_actual_power_kw"]))

    bess_meter = maps["bess_meter"]
    bess_meter.add_input(0, 2, lambda: scale_to_words(runtime.get_engine_state()["bess_actual_power_kw"]))

    controller = maps["simulation_controller"]
    controller.add_holding(0, 2, lambda: scale_to_words(runtime.get_engine_state()["pyranometer_wm2"], 1.0), lambda words: runtime.update_inputs(pyranometer_wm2=words_to_scaled_value(words, 1.0)))
    controller.add_holding(2, 2, lambda: scale_to_words(runtime.get_engine_state()["local_load_kw"]), lambda words: runtime.update_inputs(local_load_kw=words_to_scaled_value(words)))
    controller.add_input(0, 2, lambda: scale_to_words(runtime.get_engine_state()["pyranometer_wm2"], 1.0))
    controller.add_input(2, 2, lambda: scale_to_words(runtime.get_engine_state()["local_load_kw"]))
    controller.add_input(4, 1, lambda: [1])

    return maps


class ModbusApplication:
    def __init__(self, unit_id: int, register_map: DeviceRegisterMap) -> None:
        self.unit_id = unit_id
        self.register_map = register_map

    def handle_pdu(self, unit_id: int, function_code: int, payload: bytes) -> bytes:
        if unit_id != self.unit_id:
            return self._exception(function_code, 11)

        try:
            if function_code == READ_HOLDING_REGISTERS:
                address, quantity = struct.unpack(">HH", payload)
                words = self.register_map.read("holding", address, quantity)
                return bytes([function_code, len(words) * 2]) + struct.pack(f">{len(words)}H", *words)
            if function_code == READ_INPUT_REGISTERS:
                address, quantity = struct.unpack(">HH", payload)
                words = self.register_map.read("input", address, quantity)
                return bytes([function_code, len(words) * 2]) + struct.pack(f">{len(words)}H", *words)
            if function_code == WRITE_SINGLE_REGISTER:
                address, value = struct.unpack(">HH", payload)
                self.register_map.write(address, [value])
                return bytes([function_code]) + payload
            if function_code == WRITE_MULTIPLE_REGISTERS:
                address, quantity, byte_count = struct.unpack(">HHB", payload[:5])
                raw_values = payload[5:]
                if len(raw_values) != byte_count or quantity * 2 != byte_count:
                    return self._exception(function_code, 3)
                words = list(struct.unpack(f">{quantity}H", raw_values))
                self.register_map.write(address, words)
                return struct.pack(">BHH", function_code, address, quantity)
        except (KeyError, ValueError):
            return self._exception(function_code, 2)

        return self._exception(function_code, 1)

    @staticmethod
    def _exception(function_code: int, exception_code: int) -> bytes:
        return bytes([function_code | 0x80, exception_code])


class ThreadedModbusTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_class: type[socketserver.BaseRequestHandler], application: ModbusApplication):
        super().__init__(server_address, handler_class)
        self.application = application


class ModbusTcpRequestHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        while True:
            header = self.request.recv(7)
            if len(header) < 7:
                return
            transaction_id, protocol_id, length, unit_id = struct.unpack(">HHHB", header)
            if protocol_id != 0 or length < 2:
                return
            payload = self._recv_exact(length - 1)
            if payload is None:
                return
            function_code = payload[0]
            response_pdu = self.server.application.handle_pdu(unit_id, function_code, payload[1:])
            response_header = struct.pack(">HHHB", transaction_id, 0, len(response_pdu) + 1, unit_id)
            self.request.sendall(response_header + response_pdu)

    def _recv_exact(self, size: int) -> bytes | None:
        chunks = bytearray()
        while len(chunks) < size:
            packet = self.request.recv(size - len(chunks))
            if not packet:
                return None
            chunks.extend(packet)
        return bytes(chunks)


@dataclass(slots=True)
class ModbusServerHandle:
    name: str
    server: ThreadedModbusTCPServer

    def start(self) -> None:
        self.server.serve_forever(poll_interval=0.2)

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def create_modbus_servers(runtime: SimulationRuntime, modbus_config: ModbusConfig) -> list[ModbusServerHandle]:
    register_maps = build_register_maps(runtime)
    device_configs: list[tuple[str, ModbusDeviceConfig]] = [
        ("pv_inverter", modbus_config.pv_inverter),
        ("pcs_inverter", modbus_config.pcs_inverter),
        ("grid_meter", modbus_config.grid_meter),
        ("pv_meter", modbus_config.pv_meter),
        ("bess_meter", modbus_config.bess_meter),
        ("simulation_controller", modbus_config.simulation_controller),
    ]
    servers: list[ModbusServerHandle] = []
    for name, device_config in device_configs:
        if not device_config.enabled:
            continue
        application = ModbusApplication(device_config.unit_id, register_maps[name])
        server = ThreadedModbusTCPServer((device_config.host, device_config.port), ModbusTcpRequestHandler, application)
        servers.append(ModbusServerHandle(name=name, server=server))
    return servers
