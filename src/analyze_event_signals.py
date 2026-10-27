import os, json
from datetime import date, timedelta
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
import psycopg2
import pandas as pd

DB_URL = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")

def get_info_conn():
    env = {}
    with open("/home/bvb/bvb-info/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    url = env["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)

def get_events_and_prices():
    conn = psycopg2.connect(DB_URL)
    events = pd.read_sql("""
        SELECT symbol, action_type AS event_type, ex_date AS effective_date
        FROM corporate_actions
        WHERE status = 'verified'
        ORDER BY ex_date
    """, conn)
    conn.close()
    iconn = get_info_conn()
    prices = pd.read_sql("""
        SELECT symbol, trade_date, close
        FROM historical_ohlcv_tradeville
        ORDER BY symbol, trade_date
    """, iconn)
    iconn.close()
    # ajusteaza preturile pentru evenimente: ratio-ul real se calculeaza din gap-ul de pret la ex_date
    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    prices = prices.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    for _, ev in events.iterrows():
        sym, exd = ev["symbol"], pd.Timestamp(ev["effective_date"])
        sub = prices[prices["symbol"] == sym]
        prev_rows = sub[sub["trade_date"] < exd]
        at_rows = sub[sub["trade_date"] == exd]
        if prev_rows.empty or at_rows.empty:
            continue
        prev_close = prev_rows.iloc[-1]["close"]
        at_close = at_rows.iloc[-1]["close"]
        if prev_close and at_close and prev_close != at_close:
            ratio = prev_close / at_close
            if abs(ratio - 1) > 0.3:  # doar gapuri mari = split/bonus real
                mask = (prices["symbol"] == sym) & (prices["trade_date"] < exd)
                prices.loc[mask, "close"] = prices.loc[mask, "close"] / ratio
    return events, prices

def analyze():
    events, prices = get_events_and_prices()
    prices = prices.sort_values(["symbol", "trade_date"])
    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    price_idx = prices.set_index(["symbol", "trade_date"])["close"]
    rows = []
    for _, ev in events.iterrows():
        sym, etype, edate = ev["symbol"], ev["event_type"], pd.Timestamp(ev["effective_date"])
        base = price_idx.get((sym, edate))
        if base is None or pd.isna(base) or base == 0:
            continue
        row = {"symbol": sym, "event_type": etype, "effective_date": edate}
        for d in range(1, 11):
            dt = edate + timedelta(days=d)
            px = price_idx.get((sym, dt))
            row[f"D+{d}"] = (px / base - 1) * 100 if px is not None and pd.notna(px) else None
        # exclude evenimentele cu D+1 extrem (probabile erori de date)
        if row["D+1"] is not None and abs(row["D+1"]) > 50:
            continue
        rows.append(row)
    df = pd.DataFrame(rows)
    ret_cols = [f"D+{d}" for d in range(1, 11)]
    # winsorization: limiteaza randamentele la ±30% ca sa reduca impactul erorilor de date
    for c in ret_cols:
        df[c] = df[c].clip(-30, 30)
    summary = df.groupby("event_type")[ret_cols].agg(["mean", "median", "count"])
    return df, summary

if __name__ == "__main__":
    df, summary = analyze()
    print(summary.round(2).to_string())
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/event_signals_detailed.csv", index=False)
    summary.round(4).to_csv("data/processed/event_signals_summary.csv")
    print(f"\nAnaliză completă: {len(df)} evenimente procesate.")
    print("Rezultate salvate în data/processed/event_signals_detailed.csv și event_signals_summary.csv")
