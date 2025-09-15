import React, { useEffect, useMemo, useRef, useState } from "react";
import mqtt from "mqtt";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from "recharts";

/**
 * MQTTDashboard.jsx
 *
 * A single-file React dashboard that connects to an MQTT broker over WebSockets,
 * subscribes to `job/status` and `jobshop/status`, and visualizes live machine telemetry.
 *
 * Requirements:
 *   npm i mqtt recharts
 *
 * Optional styling: TailwindCSS (for the classes used here).
 */

const DEFAULT_BROKER =
  import.meta?.env?.VITE_MQTT_WS_URL || "ws://localhost:8083"; // WS listener; path will be normalized to /mqtt
const STATUS_TOPIC = "job/status";      // per-tick machine telemetry
const EVENT_TOPIC = "jobshop/status";   // lifecycle events (STARTED/COMPLETED/FAILED)

// Utility to format timestamps shown on charts/logs
function fmtClock(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString();
}

// A small colored dot to show connection status
function StatusDot({ online }) {
  return (
    <span
      className={`inline-block h-3 w-3 rounded-full mr-2 ${
        online ? "bg-green-500" : "bg-rose-500"
      }`}
      title={online ? "Connected" : "Disconnected"}
    />
  );
}

export default function MQTTDashboard() {
  const clientRef = useRef(null);
  const [brokerUrl, setBrokerUrl] = useState(DEFAULT_BROKER);
  const [isConnected, setIsConnected] = useState(false);

  // Machine state map keyed by machine_id
  const [machines, setMachines] = useState({});
  // History: map of machine_id -> array of { t, temperature, vibration }
  const historiesRef = useRef({});
  const [, forceTick] = useState(0); // trigger rerenders for history updates

  // Activity log for jobshop/status
  const [events, setEvents] = useState([]); // { ts, type, machine_id, job_id?, reason? }

  // Selected machine for the big chart
  const machineIds = useMemo(() => Object.keys(machines).sort(), [machines]);
  const [selectedMachine, setSelectedMachine] = useState("");

  useEffect(() => {
    if (!selectedMachine && machineIds.length) setSelectedMachine(machineIds[0]);
  }, [machineIds, selectedMachine]);

  // Connect / reconnect to MQTT
  const connect = () => {
    try {
      // Clean up previous connection if any
      if (clientRef.current) {
        try {
          clientRef.current.end(true);
        } catch {}
        clientRef.current = null;
      }

      // --- normalize URL: add /mqtt if user typed just ws://host:port ---
      const raw = brokerUrl.trim();
      let finalUrl = raw;
      try {
        const u = new URL(raw);
        if (u.protocol.startsWith("ws") && (u.pathname === "/" || u.pathname === "")) {
          u.pathname = "/mqtt"; // Mosquitto's common WS path
          finalUrl = u.toString();
        }
      } catch {
        // ignore invalid URL, pass as-is
      }

      const client = mqtt.connect(finalUrl, {
        // Add username/password here if your broker requires it
        reconnectPeriod: 2000,
        keepalive: 30,
      });

      client.on("connect", () => {
        setIsConnected(true);
        client.subscribe(STATUS_TOPIC);
        client.subscribe(EVENT_TOPIC);
      });

      client.on("reconnect", () => setIsConnected(false));
      client.on("close", () => setIsConnected(false));
      client.on("offline", () => setIsConnected(false));
      client.on("error", (err) => {
        console.error("MQTT error:", err);
      });

      client.on("message", (topic, payload) => {
        // Try to parse JSON; if not JSON, ignore
        let obj = null;
        try {
          obj = JSON.parse(payload.toString());
        } catch {}
        if (!obj) return;

        const now = Date.now();

        if (topic === STATUS_TOPIC) {
          // Expected payload from backend:
          // {
          //   timestamp, machine_id, class_name, temperature, vibration,
          //   status, current_job, temp_threshold, vib_threshold
          // }
          const mId = obj.machine_id;
          // Update machine snapshot
          setMachines((prev) => ({
            ...prev,
            [mId]: {
              machine_id: mId,
              class_name: obj.class_name,
              temperature: obj.temperature,
              vibration: obj.vibration,
              status: obj.status,
              current_job: obj.current_job,
              temp_threshold: obj.temp_threshold,
              vib_threshold: obj.vib_threshold,
              lastSeen: now,
            },
          }));

          // Append to history (cap at 300 points per machine)
          if (!historiesRef.current[mId]) historiesRef.current[mId] = [];
          const arr = historiesRef.current[mId];
          arr.push({ t: now, temperature: obj.temperature, vibration: obj.vibration });
          if (arr.length > 300) arr.shift();
          forceTick((x) => x + 1); // trigger chart re-render
        }

        if (topic === EVENT_TOPIC) {
          // Expected: {type, timestamp, machine_id, job_id?, reason?, ...}
          setEvents((prev) => {
            const next = [
              {
                ts: obj.timestamp ? obj.timestamp * 1000 : now,
                type: obj.type,
                machine_id: obj.machine_id,
                job_id: obj.job_id,
                reason: obj.reason,
              },
              ...prev,
            ];
            return next.slice(0, 200);
          });
        }
      });

      clientRef.current = client;
    } catch (e) {
      console.error("Failed to connect:", e);
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (clientRef.current) {
        try {
          clientRef.current.end(true);
        } catch {}
        clientRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Build chart data for selected machine
  const chartData = useMemo(() => {
    const arr = historiesRef.current[selectedMachine] || [];
    // recharts expects objects; convert timestamp to a small label
    return arr.map((p) => ({
      time: fmtClock(p.t),
      temperature: p.temperature,
      vibration: p.vibration,
    }));
  }, [selectedMachine, machines]);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-neutral-900/70 backdrop-blur border-b border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <StatusDot online={isConnected} />
            <h1 className="text-lg font-semibold tracking-wide">MQTT Shopfloor Dashboard</h1>
          </div>
          <div className="flex items-center gap-2">
            <input
              className="bg-neutral-800 border border-neutral-700 rounded px-3 py-1 text-sm w-64"
              placeholder="ws://localhost:8083"
              value={brokerUrl}
              onChange={(e) => setBrokerUrl(e.target.value)}
            />
            <button
              onClick={connect}
              className="px-3 py-1 rounded bg-sky-600 hover:bg-sky-500 text-sm font-medium"
            >
              Connect
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-8">
        {/* Machines grid */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-neutral-200">Machines</h2>
            <span className="text-xs text-neutral-400">
              Topics: <code>job/status</code>, <code>jobshop/status</code>
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {machineIds.length === 0 && (
              <div className="col-span-full text-neutral-400 text-sm">
                No machines yet. Waiting for messages…
              </div>
            )}
            {machineIds.map((mId) => (
              <MachineCard
                key={mId}
                data={machines[mId]}
                onSelect={() => setSelectedMachine(mId)}
                selected={selectedMachine === mId}
              />
            ))}
          </div>
        </section>

        {/* Timeseries */}
        <section className="bg-neutral-900 border border-neutral-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-neutral-200">Live Telemetry</h3>
              <p className="text-xs text-neutral-400">Temperature & Vibration over time</p>
            </div>
            <select
              className="bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-sm"
              value={selectedMachine}
              onChange={(e) => setSelectedMachine(e.target.value)}
            >
              {machineIds.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
                <XAxis dataKey="time" tick={{ fill: "#b3b3b3", fontSize: 12 }} />
                <YAxis yAxisId="left" tick={{ fill: "#b3b3b3", fontSize: 12 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: "#b3b3b3", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0a0a0a", border: "1px solid #333", color: "#fff" }} />
                <Legend wrapperStyle={{ color: "#d4d4d4" }} />
                <Line yAxisId="left" type="monotone" dataKey="temperature" dot={false} strokeWidth={2} name="Temperature" />
                <Line yAxisId="right" type="monotone" dataKey="vibration" dot={false} strokeWidth={4} name="Vibration"  />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Event log */}
        <section className="bg-neutral-900 border border-neutral-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-neutral-200">Activity Log</h3>
            <button
              onClick={() => setEvents([])}
              className="text-xs px-2 py-1 rounded border border-neutral-700 hover:bg-neutral-800"
            >
              Clear
            </button>
          </div>
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-neutral-400 border-b border-neutral-800">
                  <th className="py-2 pr-2">Time</th>
                  <th className="py-2 pr-2">Type</th>
                  <th className="py-2 pr-2">Machine</th>
                  <th className="py-2 pr-2">Job</th>
                  <th className="py-2 pr-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 && (
                  <tr>
                    <td className="py-3 text-neutral-500" colSpan={5}>
                      No events yet…
                    </td>
                  </tr>
                )}
                {events.map((e, idx) => (
                  <tr key={idx} className="border-b border-neutral-900">
                    <td className="py-2 pr-2 whitespace-nowrap">{fmtClock(e.ts)}</td>
                    <td className="py-2 pr-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          e.type === "FAILED"
                            ? "bg-rose-900/40 text-rose-300 border border-rose-800/60"
                            : e.type === "COMPLETED"
                            ? "bg-emerald-900/40 text-emerald-300 border border-emerald-800/60"
                            : "bg-sky-900/40 text-sky-300 border border-sky-800/60"
                        }`}
                      >
                        {e.type || "EVENT"}
                      </span>
                    </td>
                    <td className="py-2 pr-2">{e.machine_id || "-"}</td>
                    <td className="py-2 pr-2">{e.job_id || "-"}</td>
                    <td className="py-2 pr-2">{e.reason || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

function MachineCard({ data, onSelect, selected }) {
  if (!data) return null;
  const pctTemp = Math.min(100, Math.round((data.temperature / data.temp_threshold) * 100));
  const pctVib = Math.min(100, Math.round((data.vibration / data.vib_threshold) * 100));

  const statusColor = data.status.startsWith("Repairing")
    ? "text-amber-300"
    : data.status === "Operational"
    ? "text-emerald-300"
    : "text-neutral-300";

  const ring = selected ? "ring-2 ring-sky-500" : "ring-0";

  return (
    <button
      onClick={onSelect}
      className={`text-left bg-neutral-900 border border-neutral-800 ${ring} rounded-2xl p-4 w-full hover:border-neutral-700 transition`}
    >
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-sm text-neutral-400">{data.class_name}</div>
          <div className="text-lg font-semibold tracking-wide">{data.machine_id}</div>
        </div>
        <div className={`text-xs font-medium ${statusColor}`}>{data.status}</div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Metric label="Temperature" value={`${data.temperature.toFixed(1)}°C`} percent={pctTemp} />
        <Metric label="Vibration" value={data.vibration.toFixed(2)} percent={pctVib} />
      </div>

      <div className="mt-3 text-xs text-neutral-400">
        Current Job: <span className="text-neutral-200 font-medium">{data.current_job}</span>
      </div>

      <div className="mt-2 text-[10px] text-neutral-500">
        T-thresh: {data.temp_threshold} · V-thresh: {data.vib_threshold}
      </div>

      <div className="mt-2 text-[10px] text-neutral-600">Last seen: {fmtClock(data.lastSeen)}</div>
    </button>
  );
}

function Metric({ label, value, percent }) {
  const bar = percent;
  const barColor = bar >= 90 ? "bg-rose-500" : bar >= 70 ? "bg-amber-400" : "bg-emerald-500";
  return (
    <div>
      <div className="text-xs text-neutral-400 mb-1">{label}</div>
      <div className="text-sm font-semibold mb-1">{value}</div>
      <div className="h-2 rounded bg-neutral-800 overflow-hidden">
        <div className={`h-full ${barColor}`} style={{ width: `${Math.max(5, bar)}%` }} />
      </div>
      <div className="text-[10px] text-neutral-500 mt-1">{percent}% of threshold</div>
    </div>
  );
}
