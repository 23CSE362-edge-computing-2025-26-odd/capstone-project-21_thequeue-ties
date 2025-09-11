# reader.py
import argparse
import json
import sys
from datetime import datetime
import paho.mqtt.client as mqtt

def pretty(payload: bytes) -> str:
    s = payload.decode("utf-8", errors="replace")
    try:
        obj = json.loads(s)
        return json.dumps(obj, indent=2, sort_keys=True)
    except json.JSONDecodeError:
        return s  # not JSON, print raw

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Connected")
        for t in userdata["topics"]:
            client.subscribe(t, qos=0)
            print(f"[MQTT] Subscribed to: {t}")
    else:
        print(f"[MQTT] Connect failed rc={rc}")

def on_message(client, userdata, msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{now}] Topic: {msg.topic}")
    print(pretty(msg.payload))
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Simple MQTT reader for job/status & jobshop/status")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--topics", nargs="*", default=["job/status", "jobshop/status"],
                        help="Topics to subscribe to (space-separated). Supports wildcards.")
    args = parser.parse_args()

    client = mqtt.Client(userdata={"topics": args.topics})
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(args.broker, args.port, keepalive=60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[MQTT] Shutting down…")
        client.disconnect()

if __name__ == "__main__":
    main()
