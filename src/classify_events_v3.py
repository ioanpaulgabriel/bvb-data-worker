import os, sys
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import psycopg2
import requests
import xml.etree.ElementTree as ET

WS_URL = "https://ws.bvb.ro/BVBFinancialsWS/CompaniesAndSecurities.asmx"
NS = {"bvb": "https://www.bvb.ro"}

KEYWORDS = [
    ("dividend", ["dividend"]),
    ("split", ["split", "fractiune", "divizare"]),
    ("bonus_issue", ["gratuitate", "bonus"]),
    ("capital_increase", ["majorare", "majorarii capitalului", "emisiune de actiuni"]),
    ("merger", ["fuziune", "absorbtie"]),
    ("name_change", ["schimbare denumire", "redenumire"]),
    ("delisting", ["radiere", "delisting"]),
    ("tender_offer", ["oferta publica", "opa"]),
]

def get_conn():
    url = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)

def fetch_news(symbol, start, end):
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetIssueNews xmlns="https://www.bvb.ro">
      <IdentityType>Symbol</IdentityType>
      <Identity>{symbol}</Identity>
      <StartDate>{start}T00:00:00</StartDate>
      <EndDate>{end}T00:00:00</EndDate>
      <Language>Romanian</Language>
    </GetIssueNews>
  </soap:Body>
</soap:Envelope>"""
    r = requests.post(WS_URL, data=body, headers={"Content-Type": "text/xml; charset=utf-8"}, timeout=30)
    r.raise_for_status()
    return r.text

def classify_news(xml_text):
    root = ET.fromstring(xml_text)
    for news in root.iter():
        if news.tag.endswith("NewsInfo"):
            cat = (news.findtext("bvb:Category", default="", namespaces=NS) or "").lower()
            sub = (news.findtext("bvb:SubCategory", default="", namespaces=NS) or "").lower()
            desc = (news.findtext("bvb:Description", default="", namespaces=NS) or "").lower()
            links = " ".join((l.text or "").lower() for l in news.findall(".//bvb:string", namespaces=NS))
            text = cat + " " + sub + " " + desc + " " + links
            for etype, kws in KEYWORDS:
                if any(kw in text for kw in kws):
                    return etype
    return None

def main():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, symbol, ex_date FROM corporate_actions WHERE status='verified' AND action_type='other'")
    rows = cur.fetchall()
    print(f"Evenimente de clasificat: {len(rows)}")
    updated = 0
    for eid, sym, exd in rows:
        start = (exd - timedelta(days=30)).isoformat()
        end = (exd + timedelta(days=5)).isoformat()
        try:
            cur.execute("SAVEPOINT sp")
            xml = fetch_news(sym, start, end)
            etype = classify_news(xml)
            if etype:
                cur.execute("UPDATE corporate_actions SET action_type=%s WHERE id=%s", (etype, eid))
                updated += 1
            cur.execute("RELEASE SAVEPOINT sp")
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp")
            print(f"Eroare {sym}: {e}", file=sys.stderr)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Evenimente reclasificate: {updated}")

if __name__ == "__main__":
    main()
