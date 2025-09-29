
---

# Shopfloor Simulation Dashboard

A real-time **job shop simulator** with **machine telemetry, failure prediction (ML), and a live React dashboard**.
It uses **MQTT** for event streaming and `paho-mqtt` (Python) + `mqtt.js` (React) for messaging.

---

## 🛠️ Requirements

* **Python 3.9+**
* **Node.js 18+ / npm**
* MQTT Broker (e.g. [Eclipse Mosquitto](https://mosquitto.org/)) running on:

  * TCP: `localhost:1883`
  * WebSocket: `localhost:8083/mqtt`

---

## 📂 Project Structure

```
.
├── simulation/
│   ├── simulation.py      # Main Python simulation
│   ├── machines.py        # Machine model
│   ├── jobs.py            # Job model
│   ├── failure_rf.pkl     # Trained RandomForest model
│   └── model_meta.json    # Threshold metadata
│
└── dashboard/
    ├── src/MQTTDashboard.jsx   # React frontend (main dashboard)
    ├── package.json
    └── vite.config.js
```

---

## ⚙️ Backend (Simulation)

1. **Create venv and install deps**:

```bash
cd simulation
python -m venv venv
source venv/bin/activate   # (or venv\Scripts\activate on Windows)
pip install -r requirements.txt
```

`requirements.txt` should include:

```
paho-mqtt
pandas
joblib
```

2. **Run Mosquitto broker** (if not already running):

```bash
# Debian/Ubuntu
sudo apt install mosquitto mosquitto-clients
mosquitto -c /etc/mosquitto/mosquitto.conf
```

Make sure **WebSockets are enabled** on port `8083`. Example snippet in `mosquitto.conf`:

```
listener 8083
protocol websockets

listener 1883
protocol mqtt
```

3. **Run simulation**:

```bash
python simulation.py
```

The sim will publish:

* `job/status` → machine snapshots (retained)
* `jobshop/status` → job lifecycle events (STARTED, STEP_DONE, FAILED, etc.)
* `job/telemetry` → per-tick telemetry stream

---

## 💻 Frontend (Dashboard)

1. **Install deps**:

```bash
cd dashboard
npm install
```

2. **Start dev server**:

```bash
npm run dev
```

Default: [http://localhost:5173](http://localhost:5173)

3. **Dashboard Components**:

* **Machines grid**: live machine cards (temperature/vibration/repair state).
* **QueueLine**: sleek single-line animated queue (replaces Gantt).
* **Telemetry**: temperature + vibration charts with markers.
* **Activity Log**: chronological event list.

---

## 🚀 Workflow

1. Start Mosquitto broker (`1883` + `8083/mqtt`).
2. Run `python simulation.py`.
3. Start React dashboard with `npm run dev`.
4. Connect via dashboard input (defaults to `ws://localhost:8083`).

---

## 🔧 Customization

* Change number of initial jobs:

```python
sim = WorkspaceSimulation(tick_seconds=1.0, seed_jobs=4)
```

* Adjust ML threshold in `model_meta.json` or environment.

* Queue job block height:
  Inside `MQTTDashboard.jsx → QueueLine`, tweak:

```jsx
<div
  className={...}
  style={{
    background: ...,
    paddingTop: "1rem",   // increase vertical space
    paddingBottom: "1rem"
  }}
>
```

---

## ✅ Troubleshooting

* **Black screen in dashboard** → check console. Ensure `npm run dev` loads `MQTTDashboard.jsx`.
* **No messages** → broker not running on `8083`. Confirm Mosquitto config.
* **Too many early failures** → warmup is built in. Adjust `WARMUP_TICKS` in `simulation.py`.

---

## 📜 License

MIT – use and adapt freely.

---

