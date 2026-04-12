"""Minimal web HMI for the AC coupling simulator."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from simulator.config import SimulationConfig
from simulator.runtime import SimulationRuntime


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AC Coupling Simulator</title>
  <style>
    :root {
      --bg: #f3efe6;
      --card: #fffdf8;
      --ink: #1e2430;
      --accent: #b6532f;
      --accent-soft: #e5b59d;
      --line: #d6c8b8;
      --good: #2f7d4a;
      --bad: #a83e2e;
      --mono: "Consolas", "SFMono-Regular", monospace;
      --sans: "Segoe UI", "Trebuchet MS", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7ea 0, #f3efe6 35%, #ebe4d6 100%);
      min-height: 100vh;
    }
    main {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }
    h1, h2 { margin: 0 0 12px; }
    p { margin: 0 0 10px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 14px 32px rgba(54, 44, 28, 0.08);
    }
    .hero {
      display: grid;
      gap: 14px;
      padding: 24px;
      border-radius: 24px;
      background: linear-gradient(135deg, rgba(255,245,228,0.95), rgba(255,255,255,0.8));
      border: 1px solid var(--line);
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 8px;
    }
    .metric {
      padding: 12px;
      border-radius: 14px;
      background: #f9f4ec;
      border: 1px solid #e5d8c8;
    }
    .metric strong {
      display: block;
      font-size: 1.3rem;
      margin-top: 6px;
    }
    form {
      display: grid;
      gap: 10px;
    }
    label {
      display: grid;
      gap: 4px;
      font-size: 0.92rem;
    }
    input, select, button {
      font: inherit;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid #c9b6a3;
      background: white;
    }
    button {
      background: var(--accent);
      color: white;
      border: none;
      cursor: pointer;
      font-weight: 600;
    }
    button.secondary {
      background: #6c7d87;
    }
    .status-good { color: var(--good); }
    .status-bad { color: var(--bad); }
    .mono { font-family: var(--mono); }
    .note {
      font-size: 0.88rem;
      color: #5a6470;
    }
    .two {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }
    @media (max-width: 640px) {
      .two { grid-template-columns: 1fr; }
      main { padding: 14px; }
    }
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div>
      <h1>AC Coupling Simulator</h1>
      <p>Live monitor and control surface for PV, PCS/BESS, Grid and simulation inputs.</p>
      <p class="note">Modbus endpoint edits are saved into the JSON config and require a restart to take effect.</p>
    </div>
    <div class="metrics">
      <div class="metric"><span>PV Power</span><strong id="pv-power">0.0 kW</strong></div>
      <div class="metric"><span>BESS Power</span><strong id="bess-power">0.0 kW</strong></div>
      <div class="metric"><span>Grid Power</span><strong id="grid-power">0.0 kW</strong></div>
      <div class="metric"><span>Grid Direction</span><strong id="grid-direction">idle</strong></div>
      <div class="metric"><span>Pyranometer</span><strong id="pyranometer">0 W/m2</strong></div>
      <div class="metric"><span>Local Load</span><strong id="local-load">0.0 kW</strong></div>
    </div>
  </section>
  <section class="grid">
    <article class="card">
      <h2>Live Controls</h2>
      <form id="controls-form">
        <div class="two">
          <label>PV Setpoint %
            <input type="number" step="0.1" name="pv_setpoint_pct">
          </label>
          <label>PCS Setpoint %
            <input type="number" step="0.1" name="pcs_setpoint_pct">
          </label>
        </div>
        <div class="two">
          <label>Pyranometer W/m2
            <input type="number" step="1" name="pyranometer_wm2">
          </label>
          <label>Local Load kW
            <input type="number" step="0.1" name="local_load_kw">
          </label>
        </div>
        <div class="two">
          <label>Grid License kW
            <input type="number" step="0.1" name="grid_license_limit_kw">
          </label>
          <label>PV Enabled
            <select name="pv_enabled"><option value="true">true</option><option value="false">false</option></select>
          </label>
        </div>
        <label>BESS Enabled
          <select name="bess_enabled"><option value="true">true</option><option value="false">false</option></select>
        </label>
        <button type="submit">Apply Runtime Changes</button>
      </form>
      <p id="controls-status" class="note"></p>
    </article>
    <article class="card">
      <h2>Modbus Endpoints</h2>
      <form id="modbus-form"></form>
      <button id="save-modbus" class="secondary">Save Modbus Config</button>
      <p id="modbus-status" class="note"></p>
    </article>
    <article class="card">
      <h2>Live State</h2>
      <pre id="state-json" class="mono"></pre>
    </article>
  </section>
</main>
<script>
  const deviceKeys = ["pv_inverter", "pcs_inverter", "grid_meter", "pv_meter", "bess_meter", "simulation_controller"];

  function setText(id, value) {
    document.getElementById(id).textContent = value;
  }

  function fillControls(state) {
    const form = document.getElementById("controls-form");
    form.pv_setpoint_pct.value = state.pv_setpoint_pct;
    form.pcs_setpoint_pct.value = state.pcs_setpoint_pct;
    form.pyranometer_wm2.value = state.pyranometer_wm2;
    form.local_load_kw.value = state.local_load_kw;
    form.grid_license_limit_kw.value = state.grid_license_limit_kw;
    form.pv_enabled.value = String(state.pv_enabled);
    form.bess_enabled.value = String(state.bess_enabled);
  }

  function renderModbus(modbus) {
    const form = document.getElementById("modbus-form");
    form.innerHTML = "";
    for (const key of deviceKeys) {
      const cfg = modbus[key];
      const block = document.createElement("div");
      block.className = "card";
      block.style.padding = "12px";
      block.innerHTML = `
        <h3 style="margin:0 0 10px">${key}</h3>
        <div class="two">
          <label>Host<input name="${key}.host" value="${cfg.host}"></label>
          <label>Port<input name="${key}.port" type="number" value="${cfg.port}"></label>
        </div>
        <div class="two">
          <label>Unit ID<input name="${key}.unit_id" type="number" value="${cfg.unit_id}"></label>
          <label>Enabled
            <select name="${key}.enabled">
              <option value="true" ${cfg.enabled ? "selected" : ""}>true</option>
              <option value="false" ${!cfg.enabled ? "selected" : ""}>false</option>
            </select>
          </label>
        </div>`;
      form.appendChild(block);
    }
  }

  async function refreshState(initial = false) {
    const response = await fetch("/api/state");
    const payload = await response.json();
    const state = payload.state;
    setText("pv-power", `${state.pv_actual_power_kw.toFixed(1)} kW`);
    setText("bess-power", `${state.bess_actual_power_kw.toFixed(1)} kW`);
    setText("grid-power", `${state.grid_active_power_kw.toFixed(1)} kW`);
    setText("grid-direction", state.grid_direction);
    setText("pyranometer", `${state.pyranometer_wm2.toFixed(0)} W/m2`);
    setText("local-load", `${state.local_load_kw.toFixed(1)} kW`);
    document.getElementById("state-json").textContent = JSON.stringify(payload, null, 2);
    if (initial) {
      fillControls(state);
      renderModbus(payload.modbus);
    }
  }

  document.getElementById("controls-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      pv_setpoint_pct: Number(form.pv_setpoint_pct.value),
      pcs_setpoint_pct: Number(form.pcs_setpoint_pct.value),
      pyranometer_wm2: Number(form.pyranometer_wm2.value),
      local_load_kw: Number(form.local_load_kw.value),
      grid_license_limit_kw: Number(form.grid_license_limit_kw.value),
      pv_enabled: form.pv_enabled.value === "true",
      bess_enabled: form.bess_enabled.value === "true"
    };
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    document.getElementById("controls-status").textContent = result.message;
    await refreshState();
  });

  document.getElementById("save-modbus").addEventListener("click", async () => {
    const inputs = document.querySelectorAll("#modbus-form input, #modbus-form select");
    const payload = {};
    for (const key of deviceKeys) {
      payload[key] = {};
    }
    for (const input of inputs) {
      const [device, field] = input.name.split(".");
      payload[device][field] = field === "enabled" ? input.value === "true" : field === "host" ? input.value : Number(input.value);
    }
    const response = await fetch("/api/config/modbus", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    document.getElementById("modbus-status").textContent = result.message;
    await refreshState();
  });

  refreshState(true);
  setInterval(() => refreshState(false), 1000);
</script>
</body>
</html>
"""


class HmiRequestHandler(BaseHTTPRequestHandler):
    server: "HmiServer"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(HTML_PAGE)
            return
        if path == "/api/state":
            self._send_json(self.server.build_state_payload())
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or "0"))
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            self._send_json({"message": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/control":
            self.server.apply_runtime_update(payload)
            self._send_json({"message": "Runtime values updated."})
            return
        if path == "/api/config/modbus":
            self.server.save_modbus_config(payload)
            self._send_json({"message": "Modbus config saved to JSON. Restart required to rebind servers."})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class HmiServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], runtime: SimulationRuntime, config: SimulationConfig, config_path: Path):
        super().__init__(server_address, HmiRequestHandler)
        self.runtime = runtime
        self.config = config
        self.config_path = config_path

    def build_state_payload(self) -> dict:
        state = self.runtime.get_engine_state()
        return {
            "state": state,
            "modbus": self._modbus_snapshot(),
        }

    def apply_runtime_update(self, payload: dict) -> None:
        self.runtime.update_inputs(
            pv_setpoint_pct=float(payload.get("pv_setpoint_pct", self.runtime.get_engine_state()["pv_setpoint_pct"])),
            pcs_setpoint_pct=float(payload.get("pcs_setpoint_pct", self.runtime.get_engine_state()["pcs_setpoint_pct"])),
            pyranometer_wm2=float(payload.get("pyranometer_wm2", self.runtime.get_engine_state()["pyranometer_wm2"])),
            local_load_kw=float(payload.get("local_load_kw", self.runtime.get_engine_state()["local_load_kw"])),
        )
        self.runtime.set_grid_license_limit_kw(float(payload.get("grid_license_limit_kw", self.runtime.get_engine_state()["grid_license_limit_kw"])))
        if "pv_enabled" in payload:
            self.runtime.set_device_enabled("pv", bool(payload["pv_enabled"]))
        if "bess_enabled" in payload:
            self.runtime.set_device_enabled("bess", bool(payload["bess_enabled"]))

    def save_modbus_config(self, payload: dict) -> None:
        for device_name, values in payload.items():
            if not hasattr(self.config.modbus, device_name):
                continue
            device = getattr(self.config.modbus, device_name)
            device.host = str(values.get("host", device.host))
            device.port = int(values.get("port", device.port))
            device.unit_id = int(values.get("unit_id", device.unit_id))
            device.enabled = bool(values.get("enabled", device.enabled))
        self.config.save(self.config_path)

    def _modbus_snapshot(self) -> dict:
        result = {}
        for name in (
            "pv_inverter",
            "pcs_inverter",
            "grid_meter",
            "pv_meter",
            "bess_meter",
            "simulation_controller",
        ):
            device = getattr(self.config.modbus, name)
            result[name] = {
                "host": device.host,
                "port": device.port,
                "unit_id": device.unit_id,
                "enabled": device.enabled,
            }
        return result


@dataclass(slots=True)
class HmiServerHandle:
    server: HmiServer

    def start(self) -> None:
        self.server.serve_forever(poll_interval=0.2)

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def create_hmi_server(runtime: SimulationRuntime, config: SimulationConfig, config_path: Path) -> HmiServerHandle | None:
    if not config.hmi.enabled:
        return None
    server = HmiServer((config.hmi.host, config.hmi.port), runtime, config, config_path)
    return HmiServerHandle(server=server)
