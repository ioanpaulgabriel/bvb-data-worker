import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/optimized_hyperparameters.json"
OUT = ROOT / "data/strategy_status.json"

config = json.loads(CONFIG.read_text())
params = config["parameters"]
metrics = config.get("train_metrics", {})

status = {
    "strategy": "atr_portfolio_mean_reversion",
    "version": "2026-10-15",
    "status": "ok",
    "parameters": {
        "holding_days": params["holding_days"],
        "min_volume_ratio": params["min_volume_ratio"],
        "use_stop_loss": False,
    },
    "validation": {
        "split": "holdout_2025_2026",
        "trades": 109,
        "net_profit_factor": 1.267,
        "win_rate": 0.431,
        "sharpe": 1.32,
        "max_drawdown": -0.110,
        "total_pnl": 12982.83,
    },
    "runtime": {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "signals_generated": 0,
        "open_positions": 0,
        "errors": [],
    },
}

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(status, indent=2))
print(f"Status publicat: {OUT}")

# BEGIN ATR MQTT PUBLISH
import paho.mqtt.publish as mqtt_publish

mqtt_config_path = Path.home() / ".config" / "bvb-data-worker" / "mqtt.json"
mqtt_config = json.loads(mqtt_config_path.read_text())

mqtt_publish.single(
    topic=mqtt_config["topic"],
    payload=OUT.read_text(),
    hostname=mqtt_config["hostname"],
    port=mqtt_config["port"],
    qos=1,
    retain=True,
    auth={
        "username": mqtt_config["username"],
        "password": mqtt_config["password"],
    },
)

print(f"Publicare MQTT confirmata: {mqtt_config['topic']}")
# END ATR MQTT PUBLISH
