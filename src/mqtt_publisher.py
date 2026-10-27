"""Publică statusul Event Risk Guard pe MQTT pentru senzori Home Assistant."""
import os, json, sys
from datetime import date
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASS = os.getenv("MQTT_PASSWORD")
PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "homelab/bvb-info").rstrip("/")

def publish(topic_suffix, payload):
    topic = f"{PREFIX}/{topic_suffix.lstrip('/')}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    info = client.publish(topic, json.dumps(payload, default=str, ensure_ascii=False), qos=1, retain=True)
    info.wait_for_publish(timeout=10)
    client.loop_stop()
    client.disconnect()
    print(f"Published: {topic}")

def main():
    live = json.load(open("output/live_signal_status.json"))
    exit_status = json.load(open("output/auto_exit_status.json")) if os.path.exists("output/auto_exit_status.json") else {}
    if live.get("date") != str(date.today()):
        print("STALE_STATUS"); sys.exit(1)
    publish("risk/status", {
        "date": live["date"],
        "blocked_count": live["blocked_count"],
        "blocked_symbols": live["blocked_symbols"],
        "exposed_count": exit_status.get("exposed_count", 0),
        "exposed_symbols": list(exit_status.get("exposed_to_blocked", {}).keys()),
    })
    publish("signals/status", {
        "date": live["date"],
        "entry_count": live.get("entry_count", 0),
        "exit_count": live.get("exit_count", 0),
        "signals": live.get("signals", []),
    })

if __name__ == "__main__":
    main()
