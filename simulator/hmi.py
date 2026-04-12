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
from simulator.service_manager import ModbusServiceManager


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AC Coupling Simulator</title>
  <style>
    :root {
      --card: rgba(255, 251, 243, 0.95);
      --ink: #1e2430;
      --accent: #b6532f;
      --line: #d6c8b8;
      --mono: "Consolas", "SFMono-Regular", monospace;
      --sans: "Segoe UI", "Trebuchet MS", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background: radial-gradient(circle at top left, #fff7ea 0, #f2ecdf 30%, #e7ddcc 100%);
      min-height: 100vh;
    }
    main {
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
    }
    h1, h2, h3 { margin: 0 0 12px; }
    p { margin: 0 0 10px; }
    .hero, .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 14px 32px rgba(54, 44, 28, 0.08);
    }
    .hero {
      padding: 24px;
      display: grid;
      gap: 14px;
    }
    .nav {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 6px;
    }
    .nav a {
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      text-decoration: none;
      color: var(--ink);
      border: 1px solid #d6c8b8;
      background: rgba(255,255,255,0.72);
      font-size: 0.92rem;
    }
    .nav a.active {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .meter-groups {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 8px;
    }
    .meter-group {
      padding: 12px;
      border-radius: 16px;
      background: #f9f4ec;
      border: 1px solid #e5d8c8;
    }
    .meter-group h3 {
      margin: 0 0 10px;
      font-size: 0.98rem;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 0;
    }
    .metric {
      padding: 12px;
      border-radius: 14px;
      background: #fffdf8;
      border: 1px solid #eadfce;
    }
    .metric strong {
      display: block;
      font-size: 1.3rem;
      margin-top: 6px;
    }
    .dashboard {
      display: grid;
      grid-template-columns: minmax(480px, 1.45fr) minmax(360px, 0.95fr);
      gap: 18px;
      margin-top: 18px;
      align-items: start;
    }
    .stack {
      display: grid;
      gap: 18px;
    }
    .card {
      padding: 18px;
      min-width: 0;
    }
    .chart-wrap {
      border-radius: 16px;
      border: 1px solid #ddcdbb;
      background: linear-gradient(180deg, #fffdf8, #f6efe4);
      padding: 12px;
      overflow: hidden;
    }
    .chart-meta {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 10px;
      font-size: 0.9rem;
    }
    .legend {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .legend-swatch {
      width: 14px;
      height: 3px;
      border-radius: 999px;
      display: inline-block;
    }
    .chart-svg {
      width: 100%;
      height: 300px;
      display: block;
    }
    form {
      display: grid;
      gap: 10px;
    }
    .production-grid, .pill-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
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
    .kpi {
      padding: 12px;
      border-radius: 14px;
      border: 1px solid #e2d4c5;
      background: #f9f4ec;
    }
    .kpi span {
      display: block;
      font-size: 0.84rem;
      color: #635748;
    }
    .kpi strong {
      display: block;
      margin-top: 6px;
      font-size: 1.15rem;
    }
    .json-view {
      max-height: 420px;
      overflow: auto;
      margin: 0;
      padding: 14px;
      border-radius: 14px;
      background: #201d1a;
      color: #efe7dc;
      font-family: var(--mono);
      font-size: 0.86rem;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .note {
      font-size: 0.88rem;
      color: #5a6470;
    }
    @media (max-width: 1100px) {
      .dashboard { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      main { padding: 14px; }
      .metrics { grid-template-columns: 1fr; }
      .production-grid, .pill-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div>
      <h1>AC Coupling Simulator</h1>
      <p>Operational view for live production, battery response, and grid behavior.</p>
      <div class="nav">
        <a class="active" href="/">Operations</a>
        <a href="/modbus">Modbus Config</a>
      </div>
    </div>
    <div class="meter-groups">
      <div class="meter-group">
        <h3>PV Meter</h3>
        <div class="metrics">
          <div class="metric"><span>Power</span><strong id="pv-power">0.0 kW</strong></div>
          <div class="metric"><span>Reactive</span><strong id="pv-reactive">0.0 kVAr</strong></div>
          <div class="metric"><span>Cos Phi</span><strong id="pv-cosphi-top">1.000</strong></div>
          <div class="metric"><span>Voltage</span><strong id="pv-voltage-top">22.0 kV</strong></div>
        </div>
      </div>
      <div class="meter-group">
        <h3>BESS Meter</h3>
        <div class="metrics">
          <div class="metric"><span>Power</span><strong id="bess-power">0.0 kW</strong></div>
          <div class="metric"><span>Reactive</span><strong id="bess-reactive">0.0 kVAr</strong></div>
          <div class="metric"><span>Cos Phi</span><strong id="bess-cosphi-top">1.000</strong></div>
          <div class="metric"><span>Voltage</span><strong id="bess-voltage-top">22.0 kV</strong></div>
        </div>
      </div>
      <div class="meter-group">
        <h3>Grid Meter</h3>
        <div class="metrics">
          <div class="metric"><span>Power</span><strong id="grid-power">0.0 kW</strong></div>
          <div class="metric"><span>Reactive</span><strong id="grid-reactive">0.0 kVAr</strong></div>
          <div class="metric"><span>Direction</span><strong id="grid-direction">idle</strong></div>
          <div class="metric"><span>Voltage</span><strong id="grid-voltage">0.0 kV</strong></div>
        </div>
      </div>
      <div class="meter-group">
        <h3>Simulation</h3>
        <div class="metrics">
          <div class="metric"><span>Pyranometer</span><strong id="pyranometer">0 W/m2</strong></div>
          <div class="metric"><span>Local Load</span><strong id="local-load">0.0 kW</strong></div>
          <div class="metric"><span>Reactive Mode</span><strong id="reactive-mode-top">Q</strong></div>
          <div class="metric"><span>Voltage Range</span><strong id="voltage-range-top">20.0 - 24.0 kV</strong></div>
        </div>
      </div>
    </div>
  </section>

  <section class="dashboard">
    <div class="stack">
      <article class="card">
        <h2>Meter Trends</h2>
        <p class="note">PV, BESS, and Grid meters are drawn on one common vertical scale.</p>
        <div class="chart-wrap">
          <div class="chart-meta">
            <span class="legend"><span class="legend-swatch" style="background:#d06a37"></span>PV meter</span>
            <span class="legend"><span class="legend-swatch" style="background:#2f7d4a"></span>BESS meter</span>
            <span class="legend"><span class="legend-swatch" style="background:#385f8a"></span>Grid meter</span>
            <span id="chart-range" class="note"></span>
          </div>
          <svg id="power-chart" class="chart-svg" viewBox="0 0 960 300" preserveAspectRatio="none"></svg>
        </div>
      </article>

      <article class="card">
        <h2>Runtime Summary</h2>
        <p class="note">Current in-memory state from the simulation engine.</p>
        <pre id="state-json" class="json-view"></pre>
      </article>
    </div>

    <div class="stack">
      <article class="card">
        <h2>Production Controls</h2>
        <form id="controls-form">
          <div class="production-grid">
            <label>PV Setpoint %
              <input type="number" step="0.1" name="pv_setpoint_pct">
            </label>
            <label>PCS Setpoint %
              <input type="number" step="0.1" name="pcs_setpoint_pct">
            </label>
            <label>PV Nominal kW
              <input type="number" step="0.1" name="pv_nominal_power_kw">
            </label>
            <label>PCS Nominal kW
              <input type="number" step="0.1" name="pcs_nominal_power_kw">
            </label>
            <label>Reactive Control Mode
              <select name="reactive_control_mode">
                <option value="0">Reactive Power</option>
                <option value="1">Cos Phi</option>
              </select>
            </label>
            <label>PV Reactive Setpoint %
              <input type="number" step="0.1" name="pv_reactive_power_setpoint_pct">
            </label>
            <label>PV Cos Phi Setpoint
              <input type="number" step="0.001" min="-1" max="1" name="pv_cos_phi_setpoint">
            </label>
            <label>Pyranometer W/m2
              <input type="number" step="1" name="pyranometer_wm2">
            </label>
            <label>Local Load kW
              <input type="number" step="0.1" name="local_load_kw">
            </label>
            <label>Voltage Min kV
              <input type="number" step="0.1" name="voltage_min_kv">
            </label>
            <label>Voltage Max kV
              <input type="number" step="0.1" name="voltage_max_kv">
            </label>
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
        <h2>Production Snapshot</h2>
        <div class="pill-grid">
          <div class="kpi"><span>PV Setpoint</span><strong id="pv-setpoint-view">0.0 %</strong></div>
          <div class="kpi"><span>PCS Setpoint</span><strong id="pcs-setpoint-view">0.0 %</strong></div>
          <div class="kpi"><span>PV Available</span><strong id="pv-available-view">0.0 kW</strong></div>
          <div class="kpi"><span>Grid License</span><strong id="grid-license-view">0.0 kW</strong></div>
          <div class="kpi"><span>PV Nominal</span><strong id="pv-nominal-view">0.0 kW</strong></div>
          <div class="kpi"><span>PCS Nominal</span><strong id="pcs-nominal-view">0.0 kW</strong></div>
          <div class="kpi"><span>PV Cos Phi</span><strong id="pv-cosphi-view">1.000</strong></div>
          <div class="kpi"><span>Grid Cos Phi</span><strong id="grid-cosphi-view">1.000</strong></div>
          <div class="kpi"><span>PV Voltage</span><strong id="pv-voltage-view">22.0 kV</strong></div>
          <div class="kpi"><span>BESS Voltage</span><strong id="bess-voltage-view">22.0 kV</strong></div>
          <div class="kpi"><span>Voltage Limits</span><strong id="voltage-limits-view">20.0 - 24.0 kV</strong></div>
          <div class="kpi"><span>Reactive Mode</span><strong id="reactive-mode-view">Q</strong></div>
        </div>
      </article>
    </div>
  </section>
</main>
<script>
  function setText(id, value) {
    document.getElementById(id).textContent = value;
  }

  function fillControls(state) {
    const form = document.getElementById("controls-form");
    form.pv_setpoint_pct.value = state.pv_setpoint_pct;
    form.pcs_setpoint_pct.value = state.pcs_setpoint_pct;
    form.pv_nominal_power_kw.value = state.pv_nominal_power_kw;
    form.pcs_nominal_power_kw.value = state.pcs_nominal_power_kw;
    form.reactive_control_mode.value = String(state.reactive_control_mode);
    form.pv_reactive_power_setpoint_pct.value = state.pv_reactive_power_setpoint_pct;
    form.pv_cos_phi_setpoint.value = state.pv_cos_phi_setpoint;
    form.pyranometer_wm2.value = state.pyranometer_wm2;
    form.local_load_kw.value = state.local_load_kw;
    form.voltage_min_kv.value = state.voltage_min_kv;
    form.voltage_max_kv.value = state.voltage_max_kv;
    form.grid_license_limit_kw.value = state.grid_license_limit_kw;
    form.pv_enabled.value = String(state.pv_enabled);
    form.bess_enabled.value = String(state.bess_enabled);
  }

  function renderChart(history) {
    const svg = document.getElementById("power-chart");
    const rangeLabel = document.getElementById("chart-range");
    const width = 960;
    const height = 300;
    const left = 54;
    const right = 18;
    const top = 14;
    const bottom = 28;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const values = history.flatMap((point) => [point.pv_power_kw, point.bess_power_kw, point.grid_power_kw]);
    const amplitude = Math.max(1, ...values.map((value) => Math.abs(value)));
    const padded = amplitude * 1.15;
    const minY = -padded;
    const maxY = padded;
    const ticks = [-padded, -padded / 2, 0, padded / 2, padded];

    function yScale(value) {
      return top + ((maxY - value) / (maxY - minY)) * plotHeight;
    }

    function xScale(index) {
      if (history.length <= 1) {
        return left;
      }
      return left + (index / (history.length - 1)) * plotWidth;
    }

    function buildPath(field) {
      return history.map((point, index) => `${index === 0 ? "M" : "L"} ${xScale(index).toFixed(2)} ${yScale(point[field]).toFixed(2)}`).join(" ");
    }

    const gridLines = ticks.map((tick) => {
      const y = yScale(tick);
      return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}" stroke="${tick === 0 ? "#8c7a67" : "#d9cebe"}" stroke-width="${tick === 0 ? 1.6 : 1}" stroke-dasharray="${tick === 0 ? "" : "4 5"}" />
              <text x="${left - 10}" y="${y + 4}" text-anchor="end" font-size="12" fill="#66594c">${tick.toFixed(0)}</text>`;
    }).join("");

    const paths = [
      { field: "pv_power_kw", color: "#d06a37" },
      { field: "bess_power_kw", color: "#2f7d4a" },
      { field: "grid_power_kw", color: "#385f8a" }
    ].map((series) => `<path d="${buildPath(series.field)}" fill="none" stroke="${series.color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />`).join("");

    svg.innerHTML = `
      <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
      ${gridLines}
      <line x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}" stroke="#988673" stroke-width="1.2" />
      <line x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}" stroke="#988673" stroke-width="1.2" />
      ${paths}
    `;
    rangeLabel.textContent = `Range: ${(-padded).toFixed(0)} to ${padded.toFixed(0)} kW`;
  }

  async function refreshState(initial = false) {
    const response = await fetch("/api/state");
    const payload = await response.json();
    const state = payload.state;
    setText("pv-power", `${state.pv_actual_power_kw.toFixed(1)} kW`);
    setText("pv-reactive", `${state.pv_actual_reactive_power_kvar.toFixed(1)} kVAr`);
    setText("bess-power", `${state.bess_actual_power_kw.toFixed(1)} kW`);
    setText("bess-reactive", `${state.bess_reactive_power_kvar.toFixed(1)} kVAr`);
    setText("grid-power", `${state.grid_active_power_kw.toFixed(1)} kW`);
    setText("grid-reactive", `${state.grid_reactive_power_kvar.toFixed(1)} kVAr`);
    setText("grid-direction", state.grid_direction);
    setText("pyranometer", `${state.pyranometer_wm2.toFixed(0)} W/m2`);
    setText("local-load", `${state.local_load_kw.toFixed(1)} kW`);
    setText("grid-voltage", `${state.grid_voltage_kv.toFixed(2)} kV`);
    setText("pv-cosphi-top", state.pv_cos_phi.toFixed(3));
    setText("pv-voltage-top", `${state.pv_voltage_kv.toFixed(2)} kV`);
    setText("bess-cosphi-top", state.bess_cos_phi.toFixed(3));
    setText("bess-voltage-top", `${state.bess_voltage_kv.toFixed(2)} kV`);
    setText("reactive-mode-top", state.reactive_control_mode === 0 ? "Q" : "Cos Phi");
    setText("voltage-range-top", `${state.voltage_min_kv.toFixed(1)} - ${state.voltage_max_kv.toFixed(1)} kV`);
    setText("pv-setpoint-view", `${state.pv_setpoint_pct.toFixed(1)} %`);
    setText("pcs-setpoint-view", `${state.pcs_setpoint_pct.toFixed(1)} %`);
    setText("pv-available-view", `${state.pv_available_power_kw.toFixed(1)} kW`);
    setText("grid-license-view", `${state.grid_license_limit_kw.toFixed(1)} kW`);
    setText("pv-nominal-view", `${state.pv_nominal_power_kw.toFixed(1)} kW`);
    setText("pcs-nominal-view", `${state.pcs_nominal_power_kw.toFixed(1)} kW`);
    setText("pv-cosphi-view", state.pv_cos_phi.toFixed(3));
    setText("grid-cosphi-view", state.grid_cos_phi.toFixed(3));
    setText("pv-voltage-view", `${state.pv_voltage_kv.toFixed(2)} kV`);
    setText("bess-voltage-view", `${state.bess_voltage_kv.toFixed(2)} kV`);
    setText("voltage-limits-view", `${state.voltage_min_kv.toFixed(1)} - ${state.voltage_max_kv.toFixed(1)} kV`);
    setText("reactive-mode-view", state.reactive_control_mode === 0 ? "Q" : "Cos Phi");
    document.getElementById("state-json").textContent = JSON.stringify(payload, null, 2);
    renderChart(payload.history);
    if (initial) {
      fillControls(state);
    }
  }

  document.getElementById("controls-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      pv_setpoint_pct: Number(form.pv_setpoint_pct.value),
      pcs_setpoint_pct: Number(form.pcs_setpoint_pct.value),
      pv_nominal_power_kw: Number(form.pv_nominal_power_kw.value),
      pcs_nominal_power_kw: Number(form.pcs_nominal_power_kw.value),
      reactive_control_mode: Number(form.reactive_control_mode.value),
      pv_reactive_power_setpoint_pct: Number(form.pv_reactive_power_setpoint_pct.value),
      pv_cos_phi_setpoint: Number(form.pv_cos_phi_setpoint.value),
      pyranometer_wm2: Number(form.pyranometer_wm2.value),
      local_load_kw: Number(form.local_load_kw.value),
      voltage_min_kv: Number(form.voltage_min_kv.value),
      voltage_max_kv: Number(form.voltage_max_kv.value),
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

  refreshState(true);
  setInterval(() => refreshState(false), 1000);
</script>
</body>
</html>
"""


MODBUS_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AC Coupling Simulator - Modbus</title>
  <style>
    :root {
      --card: rgba(255, 251, 243, 0.95);
      --ink: #1e2430;
      --accent: #b6532f;
      --line: #d6c8b8;
      --sans: "Segoe UI", "Trebuchet MS", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background: radial-gradient(circle at top left, #fff7ea 0, #f2ecdf 30%, #e7ddcc 100%);
      min-height: 100vh;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 20px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 14px 32px rgba(54, 44, 28, 0.08);
      margin-top: 16px;
    }
    .nav {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .nav a {
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      text-decoration: none;
      color: var(--ink);
      border: 1px solid #d6c8b8;
      background: rgba(255,255,255,0.72);
      font-size: 0.92rem;
    }
    .nav a.active {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .devices {
      display: grid;
      gap: 12px;
    }
    .device {
      border: 1px solid #e1d4c5;
      border-radius: 14px;
      padding: 14px;
      background: #f9f4ec;
    }
    .two {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
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
      margin-top: 14px;
    }
    .note {
      font-size: 0.9rem;
      color: #5f635c;
    }
    @media (max-width: 640px) {
      .two { grid-template-columns: 1fr; }
      main { padding: 14px; }
    }
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>Modbus Configuration</h1>
    <p class="note">Edit endpoint settings here. Saved changes apply after simulator restart.</p>
    <div class="nav">
      <a href="/">Operations</a>
      <a class="active" href="/modbus">Modbus Config</a>
    </div>
  </section>
  <section class="card">
    <form id="modbus-form" class="devices"></form>
    <button id="save-modbus" type="button">Save Modbus Config</button>
    <p id="modbus-status" class="note"></p>
  </section>
</main>
<script>
  const deviceKeys = ["pv_inverter", "pcs_inverter", "grid_meter", "pv_meter", "bess_meter", "simulation_controller"];
  const setpointRegisterDevices = new Set(["pv_inverter", "pcs_inverter"]);
  const reactiveRegisterDevices = new Set(["pv_inverter"]);

  function renderModbus(modbus) {
    const form = document.getElementById("modbus-form");
    form.innerHTML = "";
    for (const key of deviceKeys) {
      const cfg = modbus[key];
      const block = document.createElement("div");
      block.className = "device";
      const setpointRow = setpointRegisterDevices.has(key)
        ? `<label>Setpoint Holding Register
             <input name="${key}.setpoint_register_address" type="number" min="0" value="${cfg.setpoint_register_address ?? 0}">
           </label>`
        : "";
      const reactiveRows = reactiveRegisterDevices.has(key)
        ? `<div class="two">
             <label>Reactive Power Register
               <input name="${key}.reactive_power_register_address" type="number" min="0" value="${cfg.reactive_power_register_address ?? 20}">
             </label>
             <label>Cos Phi Register
               <input name="${key}.cos_phi_register_address" type="number" min="0" value="${cfg.cos_phi_register_address ?? 40}">
             </label>
           </div>`
        : "";
      block.innerHTML = `
        <h3>${key}</h3>
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
        </div>
        ${setpointRow}
        ${reactiveRows}`;
      form.appendChild(block);
    }
  }

  async function refreshConfig() {
    const response = await fetch("/api/state");
    const payload = await response.json();
    renderModbus(payload.modbus);
  }

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
    await refreshConfig();
  });

  refreshConfig();
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
        if path == "/modbus":
            self._send_html(MODBUS_PAGE)
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
            message = self.server.save_modbus_config(payload)
            self._send_json({"message": message})
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
    def __init__(
        self,
        server_address: tuple[str, int],
        runtime: SimulationRuntime,
        config: SimulationConfig,
        config_path: Path,
        modbus_manager: ModbusServiceManager | None = None,
    ):
        super().__init__(server_address, HmiRequestHandler)
        self.runtime = runtime
        self.config = config
        self.config_path = config_path
        self.modbus_manager = modbus_manager

    def build_state_payload(self) -> dict:
        state = self.runtime.get_engine_state()
        return {
            "state": state,
            "modbus": self._modbus_snapshot(),
            "history": self.runtime.get_history(),
        }

    def apply_runtime_update(self, payload: dict) -> None:
        self.runtime.update_inputs(
            pv_setpoint_pct=float(payload.get("pv_setpoint_pct", self.runtime.get_engine_state()["pv_setpoint_pct"])),
            pcs_setpoint_pct=float(payload.get("pcs_setpoint_pct", self.runtime.get_engine_state()["pcs_setpoint_pct"])),
            pv_reactive_power_setpoint_pct=float(payload.get("pv_reactive_power_setpoint_pct", self.runtime.get_engine_state()["pv_reactive_power_setpoint_pct"])),
            pv_cos_phi_setpoint=float(payload.get("pv_cos_phi_setpoint", self.runtime.get_engine_state()["pv_cos_phi_setpoint"])),
            pyranometer_wm2=float(payload.get("pyranometer_wm2", self.runtime.get_engine_state()["pyranometer_wm2"])),
            local_load_kw=float(payload.get("local_load_kw", self.runtime.get_engine_state()["local_load_kw"])),
            reactive_control_mode=int(payload.get("reactive_control_mode", self.runtime.get_engine_state()["reactive_control_mode"])),
            voltage_min_kv=float(payload.get("voltage_min_kv", self.runtime.get_engine_state()["voltage_min_kv"])),
            voltage_max_kv=float(payload.get("voltage_max_kv", self.runtime.get_engine_state()["voltage_max_kv"])),
        )
        if "pv_nominal_power_kw" in payload:
            self.runtime.set_nominal_power_kw("pv", float(payload["pv_nominal_power_kw"]))
        if "pcs_nominal_power_kw" in payload:
            self.runtime.set_nominal_power_kw("bess", float(payload["pcs_nominal_power_kw"]))
        self.runtime.set_grid_license_limit_kw(float(payload.get("grid_license_limit_kw", self.runtime.get_engine_state()["grid_license_limit_kw"])))
        if "pv_enabled" in payload:
            self.runtime.set_device_enabled("pv", bool(payload["pv_enabled"]))
        if "bess_enabled" in payload:
            self.runtime.set_device_enabled("bess", bool(payload["bess_enabled"]))

    def save_modbus_config(self, payload: dict) -> str:
        for device_name, values in payload.items():
            if not hasattr(self.config.modbus, device_name):
                continue
            device = getattr(self.config.modbus, device_name)
            device.host = str(values.get("host", device.host))
            device.port = int(values.get("port", device.port))
            device.unit_id = int(values.get("unit_id", device.unit_id))
            device.enabled = bool(values.get("enabled", device.enabled))
            if "setpoint_register_address" in values:
                device.setpoint_register_address = max(0, int(values["setpoint_register_address"]))
            if "reactive_power_register_address" in values:
                device.reactive_power_register_address = max(0, int(values["reactive_power_register_address"]))
            if "cos_phi_register_address" in values:
                device.cos_phi_register_address = max(0, int(values["cos_phi_register_address"]))
        self.config.save(self.config_path)
        if self.modbus_manager is not None:
            self.modbus_manager.reload(self.config.modbus)
            return "Modbus config saved and Modbus services restarted."
        return "Modbus config saved to JSON."

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
                "setpoint_register_address": device.setpoint_register_address,
                "reactive_power_register_address": device.reactive_power_register_address,
                "cos_phi_register_address": device.cos_phi_register_address,
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


def create_hmi_server(
    runtime: SimulationRuntime,
    config: SimulationConfig,
    config_path: Path,
    modbus_manager: ModbusServiceManager | None = None,
) -> HmiServerHandle | None:
    if not config.hmi.enabled:
        return None
    server = HmiServer((config.hmi.host, config.hmi.port), runtime, config, config_path, modbus_manager=modbus_manager)
    return HmiServerHandle(server=server)
