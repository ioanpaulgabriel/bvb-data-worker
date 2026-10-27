"""Închide automat pozițiile deschise pe simbolurile care intră în fereastra de risc post-eveniment."""
import os, json, sys
from datetime import date
import psycopg2

DB_URL = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
STATUS_FILE = "output/live_signal_status.json"

def get_open_positions():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, COUNT(*) AS open_trades
        FROM strategy_trades
        WHERE exit_date >= %s
        GROUP BY symbol
    """, (date.today(),))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {r[0]: r[1] for r in rows}  # symbol -> nr. tranzacții încă deschise

def main():
    if not os.path.exists(STATUS_FILE):
        print(json.dumps({"error": "NO_STATUS_FILE"})); sys.exit(1)
    status = json.load(open(STATUS_FILE))
    if status.get("date") != str(date.today()):
        print(json.dumps({"error": "STALE_STATUS", "status_date": status.get("date")})); sys.exit(1)
    blocked = set(status.get("blocked_symbols", []))
    positions = get_open_positions()
    exposed = {s: q for s, q in positions.items() if s in blocked}
    result = {
        "date": str(date.today()),
        "open_positions": positions,
        "exposed_to_blocked": exposed,
        "exposed_count": len(exposed),
    }
    print(json.dumps(result, indent=2))
    os.makedirs("output", exist_ok=True)
    with open("output/auto_exit_status.json", "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()
