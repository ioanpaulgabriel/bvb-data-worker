import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import psycopg2
import pandas as pd

def get_conn():
    url = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)

def main():
    conn = get_conn()
    query = """
    SELECT ca.symbol, ca.ex_date, ca.action_type, p.trade_date, p.close
    FROM corporate_actions ca
    JOIN historical_ohlcv p ON p.symbol = ca.symbol AND p.trade_date BETWEEN ca.ex_date - INTERVAL '10 days' AND ca.ex_date + INTERVAL '10 days'
    WHERE ca.status='verified'
    ORDER BY ca.symbol, ca.ex_date, p.trade_date
    """
    df = pd.read_sql(query, conn)
    conn.close()
    print(f"Randuri din join: {len(df)}")
    if df.empty:
        print("Niciun rand — verificam simboluri din corporate_actions vs prices_daily")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM corporate_actions WHERE status='verified' LIMIT 5")
        print("Simboluri corporate_actions:", [r[0] for r in cur.fetchall()])
        cur.execute("SELECT DISTINCT symbol FROM prices_daily LIMIT 5")
        print("Simboluri prices_daily:", [r[0] for r in cur.fetchall()])
        cur.close(); conn.close()
        return

    results = []
    for (sym, exd, atype), g in df.groupby(["symbol", "ex_date", "action_type"]):
        g = g.sort_values("trade_date")
        base = g[g["trade_date"] <= exd].tail(1)
        if base.empty:
            continue
        base_close = base["close"].iloc[0]
        for days in [1, 5, 10]:
            future = g[g["trade_date"] > exd].head(days)
            if len(future) < days:
                continue
            ret = (future["close"].iloc[-1] / base_close - 1) * 100
            results.append({"action_type": atype, "days": days, "return_pct": ret})

    if not results:
        print("Niciun eveniment cu suficiente date de pret.")
        return
    res = pd.DataFrame(results)
    summary = res.groupby(["action_type", "days"])["return_pct"].agg(["count", "mean", "median"]).round(2)
    print(summary)
    res.to_csv("output/event_returns.csv", index=False)
    print("Rezultate salvate in output/event_returns.csv")

if __name__ == "__main__":
    main()
