# failpredict_reader.py
import json
import argparse
from datetime import datetime
import paho.mqtt.client as mqtt

ALERT_TOPIC = "job/alerts"
PRINT_ALL = False  # set True to see every alert (including red_flag = False)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] Connected → subscribing to '{ALERT_TOPIC}'")
        client.subscribe(ALERT_TOPIC, qos=0)
    else:
        print(f"[MQTT] Connect failed rc={rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return

    ts = payload.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    machine_id = payload.get("machine_id", "UNKNOWN")
    risk = payload.get("risk_score", None)
    thr  = payload.get("threshold", None)
    model = payload.get("model", "model")
    red  = bool(payload.get("red_flag"))

    if PRINT_ALL or red:
        risk_str = f"{risk:.3f}" if isinstance(risk, (int, float)) else str(risk)
        thr_str  = f"{thr:.3f}"  if isinstance(thr,  (int, float)) else str(thr)
        if red:
            print(f"[{ts}] FAIL PREDICTED → machine: {machine_id} | risk: {risk_str} (thr={thr_str}) | by {model}")
        else:
            print(f"[{ts}] alert seen → machine: {machine_id} | risk: {risk_str} (thr={thr_str}) | by {model} | red_flag=False")

def main():
    ap = argparse.ArgumentParser(description="Listen to job/alerts and print predicted failures.")
    ap.add_argument("--broker", default="localhost", help="MQTT broker address")
    ap.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    ap.add_argument("--keepalive", type=int, default=60, help="MQTT keepalive seconds")
    args = ap.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=args.keepalive)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[MQTT] Shutting down…")
        client.disconnect()

if __name__ == "__main__":
    main()
