"""Ingestie evenimente BVB: Strat A (CALENDAR din #gvCF) + Strat B (AD_HOC din feed central)."""
import os, re, sys, json
from datetime import date
import requests
from bs4 import BeautifulSoup
import psycopg2
from bvb_events_config import classify_title

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
BASE = "https://bvb.ro"
DB_URL = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")

def get_db():
    return psycopg2.connect(DB_URL)

def upsert_event(cur, symbol, event_type, event_source, title, effective_date, source_url, raw=None):
    if event_type == "UNKNOWN":
        print(f"[SKIP UNKNOWN] {symbol}: {title[:60]}", file=sys.stderr)
        return
    cur.execute("""
        INSERT INTO market_events
            (symbol, event_type, event_source, scheduled_date, effective_date,
             published_at, source_url, raw_title)
        VALUES (%s,%s,%s,%s,%s, now(), %s, %s)
        ON CONFLICT (symbol, event_type, effective_date, source_url) DO NOTHING
    """, (symbol, event_type, event_source, None, effective_date, source_url, title))

def sync_calendar(cur, symbols):
    months = {"ianuarie":1,"februarie":2,"martie":3,"aprilie":4,"mai":5,"iunie":6,
              "iulie":7,"august":8,"septembrie":9,"octombrie":10,"noiembrie":11,"decembrie":12}
    for sym in symbols:
        url = f"{BASE}/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx?s={sym}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table", id="gvCF")
            if not table:
                continue
            for row in table.find_all("tr"):
                date_div = row.find("div", class_="evDate")
                title_p = row.find("p")
                if not date_div or not title_p:
                    continue
                m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_div.get_text())
                if not m or m.group(2).lower() not in months:
                    continue
                eff = date(int(m.group(3)), months[m.group(2).lower()], int(m.group(1)))
                title = title_p.get_text(strip=True)
                upsert_event(cur, sym, classify_title(title), "CALENDAR", title, eff, url)
        except Exception as e:
            print(f"[CALENDAR] {sym}: {e}", file=sys.stderr)

def sync_adhoc(cur):
    """Strat B: feed centralizat de rapoarte curente (m.bvb.ro)."""
    url = "https://m.bvb.ro/financialinstruments/selecteddata/currentreports"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        wrap = soup.find(class_="current-reports-table")
        table = wrap.find("table") if wrap else None
        if not table:
            print("[AD_HOC] tabel negasit", file=sys.stderr)
            return
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            sym_a = cells[0].find("a")
            sym = sym_a.get_text(strip=True) if sym_a else None
            title_a = cells[2].find("a")
            title = title_a.get_text(strip=True) if title_a else cells[2].get_text(strip=True)
            if not sym or not title:
                continue
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", cells[3].get_text())
            if not m:
                continue
            eff = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            link = title_a["href"] if title_a and title_a.get("href") else url
            if link.startswith("/"):
                link = "https://m.bvb.ro" + link
            upsert_event(cur, sym, classify_title(title), "AD_HOC", title, eff, link)
    except Exception as e:
        print(f"[AD_HOC]: {e}", file=sys.stderr)

def main():
    symbols = sys.argv[1].split(",") if len(sys.argv) > 1 else []
    conn = get_db()
    cur = conn.cursor()
    if symbols:
        sync_calendar(cur, symbols)
    sync_adhoc(cur)
    conn.commit()
    cur.close(); conn.close()
    print("Sync complet.")

if __name__ == "__main__":
    main()
