"""Verifică dacă un simbol poate fi tranzacționat azi (nu e în fereastra de risc post-eveniment)."""
import os, sys, json
from datetime import date

STATUS_FILE = "output/live_signal_status.json"

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: check_trade_allowed.py SYMBOL"}))
        sys.exit(1)
    symbol = sys.argv[1].upper()
    if not os.path.exists(STATUS_FILE):
        print(json.dumps({"symbol": symbol, "allowed": False, "reason": "NO_STATUS_FILE"}))
        sys.exit(0)
    status = json.load(open(STATUS_FILE))
    if status.get("date") != str(date.today()):
        print(json.dumps({"symbol": symbol, "allowed": False, "reason": "STALE_STATUS", "status_date": status.get("date")}))
        sys.exit(0)
    blocked = symbol in status.get("blocked_symbols", [])
    print(json.dumps({
        "symbol": symbol,
        "allowed": not blocked,
        "blocked": blocked,
        "status_date": status["date"],
    }))

if __name__ == "__main__":
    main()
