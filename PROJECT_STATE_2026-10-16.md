# BVB / HOMELAB — Stare consolidată a proiectului

Data actualizării: 2026-10-16, aproximativ 07:10 Europe/Bucharest.
Scop: document de continuitate care înlocuiește snapshotul PROJECT_STATE_2026-10-14.txt pentru conversațiile viitoare. Nu este o copie completă a repository-urilor. Constatările curente provin din comenzile, codul și rezultatele furnizate de utilizator în conversația din 15–16 octombrie 2026.

## 0. Instrucțiuni de continuitate

- Prioritatea actuală este DOCUMENTAREA stării reale, nu ștergerea sau rescrierea proiectului.
- Utilizatorul a oprit explicit curățarea generală. Automatizările, datele și proiectele existente se păstrează.
- Nu continua automat planul anterior de reconstrucție de la zero; a fost discutat, nu implementat, iar direcția curentă este documentarea și clarificarea schimbărilor.
- Lucrează punctual: comandă exactă, feedback, apoi pasul următor. Nu acumula patchuri sau colectoare paralele fără justificare.
- Nu interpreta fișierele neversionate ca fiind inutile. Nu folosi git clean, git reset --hard, DROP ... CASCADE sau ștergeri globale fără inventar, backup și aprobare explicită.
- Separă: implementat și verificat / implementat dar neverificat complet / propus și neimplementat.
- Nu confunda backtestul cu un portofoliu curent, nici semnalul cu execuția.
- Nu afișa sau solicita parole, tokenuri ori conținutul .env.

## 1. Arhitectura confirmată

### 1.1 Proiecte și baze distincte

| Proiect | Director | Bază PostgreSQL | Rol confirmat |
|---|---|---|---|
| bvb-info | /home/bvb/bvb-info | bvb_info | bvb_info_app |
| bvb-data-worker | /home/bvb/bvb-data-worker | bvb_data | bvb_worker |

Pentru worker: server 127.0.0.1:5432; search_path = '"$user", public'.
Pentru bvb-info: conexiune SQLAlchemy postgresql+psycopg2, baza/rolul confirmate; adresa serverului nu a fost verificată în outputul furnizat.
PostgreSQL 17.11 pe Debian a fost raportat la inspecția bazei bvb_info.

### 1.2 Fragmentarea surselor

- bvb-info importă snapshot HTML în bvb_info.public.daily_prices.
- bvb-info.public.v_ohlcv_clean citește exclusiv bvb_info.public.historical_ohlcv.
- v_ohlcv_indicators_v2 și v_trade_candidates depind de acel istoric.
- Workerul CSV importă în bvb_data.public.prices_daily_raw și prices_daily.
- src/metrics_generator.py citește historical_ohlcv.
- src/atr_portfolio_simulator.py conține load_ohlcv() care citește historical_ohlcv.
- DAR runnerul ATR inspectat încarcă data/history/*_history.csv și transmite explicit ohlcv_by_symbol simulatorului. Existența load_ohlcv nu demonstrează că runnerul o apelează.
- Generatorul ATR inspectat citește aceleași CSV-uri de istoric.
- Nu există încă o serie canonică unificată confirmată pentru toate aceste căi.

## 2. Operare și cron

Ultimul crontab furnizat explicit conținea:

```cron
30 18 * * 1-5 cd /home/bvb/bvb-info && ./bvb_daily.sh >> logs/cron.log 2>&1
0 19 * * 1-5 cd /home/bvb/bvb-info && .venv/bin/python build_strategy_status.py && .venv/bin/python publish_strategy.py strategy_status.json >> /home/bvb/bvb-info/strategy_publish.log 2>&1
35 18 * * 1-5 cd /home/bvb/bvb-data-worker && ./scripts/daily.sh >> /home/bvb/bvb-data-worker/output/daily.log 2>&1
```

O linie suplimentară la 19:05 pentru build_portfolio_notifications.py a fost propusă, dar instalarea ei în cron NU a fost confirmată printr-un crontab ulterior.

Worker scripts/daily.sh inspectat:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/bvb/bvb-data-worker
source .venv/bin/activate
echo "[$(date '+%F %T')] Starting BVB daily pipeline"
python src/fetch_bvb.py
python src/metrics_generator.py
python scripts/publish_strategy.py
echo "[$(date '+%F %T')] BVB daily pipeline finished"
```

Logul din 15 octombrie confirmă import CSV, generare metrici și publicare pe bvb/atr_portfolio/status.

## 3. bvb-info: structură, erori și modificări persistente

### 3.1 daily_prices

Coloane: id, symbol, date, price, var_pct, open, max, min, avg, value_ron, volume, trades, market, last_time, source.
Cheie unică: (symbol, date), fără market/source.

v_ohlcv_unified există în bvb_info:
- historical_ohlcv, cu trade_date redenumit date;
- UNION ALL cu daily_prices pentru perechi (symbol,date) inexistente în historical_ohlcv;
- preferă istoricul la suprapuneri;
- nu elimină eventuale duplicate interne ale istoricului.
Verificarea furnizată nu a găsit duplicate pe (trade_date,symbol) în historical_ohlcv.

### 3.2 Erori demonstrate

1. pandas read_html convertise numerele; ro_float le transforma iar în text și putea interpreta numeric 1.305 ca 1305.
2. Fluxul ETF selecta primul tabel cu Simbol/Valoare, fără verificarea schimbării efective a tabului.
3. ETF construia obiecte fără OHLCV.
4. Pipeline-ul concatena trading + ETF; Repository.upsert_prices atribuia toate câmpurile necondiționat pe cheia (symbol,date). Rândul ETF ulterior putea șterge OHLCV și înlocui source.
5. Snapshotul includea mai multe piețe, deci existau simboluri repetate între piețe.
6. Crawlerul atribuie date.today(); data ședinței și închiderea finală nu sunt verificate explicit în sursă.

### 3.3 Patchuri aplicate și confirmate

A. bvb_scraper/parsers/numbers.py:
- numerele non-string sunt convertite direct la float, fără reinterpretare locală;
- bool și valori lipsă/nefinite sunt respinse către None;
- șirurile păstrează convenția românească;
- testele au trecut, inclusiv 1.305 numeric -> 1.305, '1.305' text -> 1305, '1,305' -> 1.305, NaN/Inf -> None.
- Este parser comun; întreaga suită de teste nu a fost confirmată ca rulată.

B. bvb_scraper/etl/pipeline.py, download_prices():
- folosește doar fetch_trading_snapshot; ETF temporar exclus;
- acceptă numai market REGS;
- verifică duplicate (symbol,date) în REGS;
- verifică open/high/low/close/volume pozitive și finite, plus low <= open/close <= high;
- exclude rândurile invalide;
- oprește importul dacă snapshotul sau rezultatul valid sunt goale;
- persistă lista validă prin repository-ul existent.
- Filtrarea afectează toți apelanții download_prices, nu doar o comandă manuală.
- Importul fetch_etf_snapshot poate rămâne neutilizat în modul; nu a fost făcută curățare ulterioară.

Repository.py a fost inspectat, NU modificat în acești pași.

### 3.4 Verificarea snapshotului din 15 octombrie

173 rânduri brute: DEALS 2, POF 1, REGS 76, XRS1 85, XRSI 9.
Duplicate între piețe: AROBS (DEALS/REGS), COTE (DEALS/REGS), PREB (POF/REGS).
Duplicate REGS: niciunul.
BIBU avea toate valorile zero; nu a fost considerat valid.

Salvare manuală filtrată reușită la aproximativ 19:01:
- received=173, accepted=76, other_markets=97, invalid=[];
- backup pentru cele 170 de rânduri existente înainte de update;
- rezultatul zilei: 76 trading/REGS și 94 rânduri etf rămase, nevalidate.

Exemple REGS persistate:
- TLV close 35.44, open 35.12, high 35.5, low 35.06, volume 794232.
- SNP close 1.305, open 1.26, high 1.309, low 1.26, volume 11995562.
- SNG close 18.9, open 18.5, high 19, low 18.5, volume 795083.
- AROBS close 0.73; COTE 75.2; PREB 2.02.

Nu au fost șterse rândurile etf și nu au fost reparate retroactiv toate zilele din bvb_info.

### 3.5 bvb_daily.sh și accesul PostgreSQL

Scriptul importă HTML, apoi folosește sudo -u postgres psql pentru jurnal și export.
Logul din 14 octombrie: import reușit, apoi sudo a eșuat deoarece cerea parolă într-un context fără terminal.
Cu set -euo pipefail, etapele următoare nu au rulat. new_signals.json=[] nu dovedește un export proaspăt fără oportunități.
Înlocuirea sudo cu Python a fost discutată, dar NU implementată în pașii confirmați.

GRANT-uri executate și verificate în bvb_info pentru bvb_info_app:
- USAGE pe schema public;
- SELECT pe v_trade_candidates și v_ohlcv_clean;
- SELECT, INSERT pe strategy_signals_log;
- USAGE pe strategy_signals_log_id_seq.
Toate cele cinci verificări au returnat True. Nu revoca automat: drepturile inițiale complete nu au fost arhivate.

strategy_signals_log:
- id bigint, default nextval('strategy_signals_log_id_seq');
- symbol, signal_date, candidate_status, strategy_version NOT NULL;
- entry_date, entry_price, rsi_14, volume_ratio_20d nullable;
- generated_at default now();
- unicitate (symbol,signal_date,strategy_version).

### 3.6 Schema provizorie bvb_paper

Crearea schemei și a v_daily_prices_valid în bvb_info a fost propusă.
Ultimul test confirmat: UndefinedTable pentru bvb_paper.v_daily_prices_valid.
Existența ulterioară a schemei NU este confirmată. Nu șterge și nu recrea fără inventar.

## 4. Vechiul flux de candidați RSI

v_trade_candidates se bazează pe v_ohlcv_indicators_v2 și historical_ohlcv:
- RSI < 30;
- lead(close), lead(high), lead(rsi), lead(date) pe simbol;
- pending_confirmation dacă next_date lipsește;
- confirmed_reversal dacă next_close > high din ziua semnalului și next_rsi > rsi;
- invalidated dacă next_close < close și next_rsi < rsi;
- altfel watchlist.

Exportul vechi include pending_confirmation și confirmed_reversal, volum >=2, dar filtrează signal_date = MAX(date) din v_ohlcv_clean.
Aceasta ratează confirmările recente ale semnalelor mai vechi: confirmarea necesită o observație ulterioară zilei semnalului.
next_close este o observație ulterioară, nu o predicție și nu un preț de execuție curent garantat.

Ultimul MAX(date) confirmat al acestei surse: 2026-10-02; multe simboluri se opresc în septembrie.
Această strategie RSI nu este identică generatorului ATR pe volum și lumânare pozitivă.

## 5. Worker CSV și backfill

### 5.1 src/fetch_bvb.py

Primește data YYYYMMDD; implicit ziua curentă.
Sursa din cod:
https://m.bvb.ro/TradingAndStatistics/Trading/HistoricalTradingInfo.ashx?day=YYYYMMDD

Persistă:
- prices_daily_raw, source=bvb_public_csv, conflict pe (trade_date,source), actualizează răspunsul;
- prices_daily, filtrat REGS, conflict pe (trade_date,symbol,source), actualizează câmpurile.
Fișiere: data/raw/YYYY-MM-DD_bvb.csv; data/clean/YYYY-MM-DD_regs.csv.

Validări prezente: coloane obligatorii, conversii numerice, prețuri >0, Low <= High, simbol REGS unic.
Nu presupune validare completă NaN/Inf, încadrare open/close în interval sau dată efectivă a ședinței: acestea nu sunt toate demonstrate în cod.
NO_DATA este returnat pentru răspuns gol înainte de scrierea raw/DB. Nu șterge datele existente pentru acea zi.
Succesul colectorului nu certifică singur corectitudinea semantică a sursei.

### 5.2 Utilitare existente

src/backfill_bvb.py:
- --start-date, --end-date, --delay;
- execută colectorul existent în subprocess, aceeași venv;
- parcurge zile calendaristice;
- clasifică SUCCESS / NO_DATA / ERROR;
- raport final și exit nenul dacă există erori.

scripts/backfill_bvb_history.py:
- alt wrapper existent;
- interval fix de aproximativ 60 de zile, doar luni-vineri;
- apelează aceeași funcție de colectare;
- nu a fost șters sau înlocuit.

### 5.3 Date confirmate înainte de backfill

În bvb_data.prices_daily:
2026-10-02:78; 10-06:86; 10-07:86; 10-08:81; 10-09:81; 10-12:82; 10-13:85; 10-14:87; 10-15:86 rânduri/simboluri.

historical_ohlcv avea observații foarte rare la final: un simbol pe zi până la 2 octombrie, două pe unele zile din septembrie; nu era actualizat prin colectorul CSV.

### 5.4 Backfill executat pe 15 octombrie

Comandă existentă, fără modificarea codului:

```bash
.venv/bin/python src/backfill_bvb.py \
  --start-date 20260901 --end-date 20261015 --delay 2
```

Rezultat pentru 45 zile calendaristice:
- SUCCESS: 5 (9,12,13,14,15 octombrie).
- NO_DATA: 39.
- ERROR: 1 (11 octombrie: RemoteDisconnected / HTTP_ERROR).

NO_DATA a apărut inclusiv pentru 2 și 6–8 octombrie, deși pentru acele zile existau deja date locale în DB.
Nu interpreta NO_DATA ca dovadă a absenței unei ședințe sau a tranzacțiilor. Cauza comportamentului sursei nu a fost stabilită.
Backfill-ul nu a completat historical_ohlcv și nici data/history/*_history.csv.
Nu a modificat codul, cronul sau HA. A persistat date/fișiere/loguri pentru cererile procesate. Datele/fișierele pentru zilele reușite puteau fi suprascrise cu versiunea nou descărcată.

## 6. Optuna — stare verificată

Versiune instalată raportată: 5.0.0, Python 3.13, venv worker.
Script: scripts/optimize_strategy.py.

Spațiu de căutare:
- holding_days categoric: 16..25;
- min_volume_ratio categoric: 1.5,2.0,2.5;
- 30 combinații posibile;
- OPTUNA_TRIALS implicit 40; numărul efectiv al rulării salvate nu este în JSON;
- direction=maximize; fără seed sau storage configurate explicit în script.

Fiecare trial:
1. setează HOLDING_DAYS, MIN_VOLUME_RATIO, SIMULATION_SPLIT=train;
2. rulează generatorul de semnale;
3. rulează runnerul de simulare;
4. citește trade/equity CSV cu sufix _train;
5. calculează metrici și scor.

Rezultat salvat în config/optimized_hyperparameters.json:

```json
{
  "parameters": {"holding_days": 18, "min_volume_ratio": 1.5},
  "train_metrics": {
    "trades": 227,
    "profit_factor": 1.5184640336636028,
    "sharpe": 2.0830243354252147,
    "max_drawdown": -0.1337330927468543,
    "total_pnl": 75315.36491979913
  },
  "score": 1.8504905209189233
}
```

Acesta este un artefact experimental, nu un rezultat validat pentru producție.
Nu este demonstrat că pipeline-ul zilnic încarcă JSON-ul cu parametri optimizați.
Nu este demonstrat că CSV-urile rămase după optimizare corespund celui mai bun trial; sunt suprascrise și pot aparține ultimului.
Nu există în JSON: dată rulare, interval date, seed, versiune cod/date, istoric trial-uri.

### 6.1 Formula scorului și limite

- pnl pe tranzacție = net_return * position_value.
- PF = suma câștigurilor / abs(suma pierderilor); dacă nu există pierderi, fixează 10.0.
- 'sharpe' folosește rezultatele pe tranzacție împărțite la 100000, apoi mean/sd * sqrt(252). Nu este un Sharpe anualizat validat pe randamente zilnice.
- max_drawdown calculat din equity-ul exportat, afectat de problema de evaluare a pozițiilor descrisă mai jos.
- penalizări: PF sub 1.10; tranzacții sub 150;
- drawdown: score -= 2 * max(0, 0.25 - abs(mdd)). Aceasta penalizează magnitudini SUB 25%, nu depășirea pragului. Dacă intenția era limita maximă, formula este inversată. Nu a fost corectată.
- Nu sunt tratate robust toate cazurile de liste goale sau artefacte vechi.
- PNL-ul calculat ca net_return*position_value nu se reconciliază exact cu cash PNL când net_return are drept bază costul de intrare inclusiv comision.

## 7. Generator ATR existent

scripts/generate_atr_portfolio_signals.py:
- citește data/history/*_history.csv;
- cere Date,Symbol,Open,High,Low,Close,Volume;
- concatenează, convertește, elimină valori lipsă, sortează pe Symbol/Date;
- TrueRange și ATR14 prin media simplă pe 14 observații;
- VolumeMA20 include observația curentă; VolumeRatio=Volume/VolumeMA20;
- MIN_VOLUME_RATIO din mediu, implicit 1.5;
- EntrySignal: indicatori disponibili, prag volum, Close>Open, Close>=0.50, VolumeMA20>=10000, Volume>=10000.

Intrarea de backtest este construită prin merge pe Symbol cu toate observațiile, filtrare NextDate>Date și drop_duplicates keep=first. Se impune o selecție explicită/verificabilă a următoarei observații; implementarea actuală are join many-to-many și se bazează pe ordinea rezultată.

HOLDING_DAYS din mediu, implicit 6. ExitSessionIndex = EntrySessionIndex + HOLDING_DAYS, pe observații disponibile ale simbolului, nu zile calendaristice garantate.
Elimină semnalele fără ExitDate viitor disponibil: adecvat doar unei selecții de tranzacții istorice completabile, nu generatorului de propuneri curente.
Output: data/atr_portfolio_signals.csv; include signal_date, entry_date, entry_price, exit_date, ATR14, VolumeRatio.

## 8. Runner ATR și split

scripts/run_atr_portfolio_simulation.py:
- citește semnalele CSV;
- SIMULATION_SPLIT = all/train/test;
- train: entry_date < 2025-01-01;
- test: entry_date >= 2025-01-01;
- filtrează intrările, nu întregul calendar OHLCV;
- încarcă integral istoricul CSV și îl transmite run_simulation();
- VolumeRatio este redenumit volume_ratio după normalizarea antetelor.

Artefacte data/atr_portfolio_simulation_trades[_train|_test].csv și equity analog.

Limitări:
- fragmentul furnizat folosește sys.path fără import sys; dacă fișierul este exact astfel pe disc, produce NameError. Nu s-a confirmat o corecție și nu s-a relansat.
- dacă semnalele inițiale sunt goale, return fără rescrierea rapoartelor: risc de citire a unor artefacte vechi de către optimizator;
- nu există verificare explicită imediat după golirea prin split;
- simbolul fișierului este luat din primul rând;
- nu verifică aici un singur simbol/fișier, duplicatele, sortarea sau OHLCV complet;
- fișiere multiple cu același simbol se pot suprascrie în dicționar.

## 9. Simulator ATR — comportament real și constatări

src/atr_portfolio_simulator.py, run_simulation la linia 465 în snapshotul inspectat.

### 9.1 Configurație declarată

- initial_cash implicit 100000.0; runnerul afișează RON.
- MAX_TOTAL_EXPOSURE=1.0; MAX_SYMBOL_EXPOSURE=0.25; MAX_ACTIVE_POSITIONS=5.
- DAILY_RISK_BUDGET=0.02; RISK_PER_TRADE=0.01.
- SIZING_ATR_MULTIPLIER=2.0; STOP_ATR_MULTIPLIER=2.0.
- ATR_MULTIPLIER=1.5 declarat, utilizare neconfirmată în fragmente.
- COST_RATE=0.005, la fiecare cumpărare/vânzare.
- MIN_VOLUME_RATIO=2.5 constant în simulator.
- USE_STOP_LOSS=False; TREND_FILTER=False; TREND_SMA_PERIOD=200.
- HOLDING_DAYS din mediu, implicit 8; utilizare în bucla principală neconfirmată, care folosește exit_date din semnal.

### 9.2 Dimensionare și execuție

calculate_position:
- stop_distance=ATR*2;
- risk_amount=equity*1%;
- position_value=min(risk_amount*entry_price/stop_distance, equity*25%);
- position_risk monetar, înaintea rotunjirii.

open_position:
- quantity=floor(position_value/entry_price);
- cost brut + 0.5% comision;
- dacă nu încape în cash, respinge, nu redimensionează automat;
- current_price inițial=entry_price.

close_position:
- încasare brută minus 0.5%;
- net_return = încasare netă / cost intrare inclusiv comision - 1.

Ordine zilnică în run_simulation:
1. eventual stopuri;
2. ieșiri planificate;
3. intrări noi;
4. equity snapshot.
Ieșire planificată la open în prima observație disponibilă la/după planned_exit_date.
Intrările folosesc trade.entry_price. ATR recalculat din observații strict anterioare intrării.
Pozițiile rămase la final nu sunt lichidate automat.

### 9.3 Probleme confirmate prin cod

A. Mark-to-market absent când stopurile sunt dezactivate:
- process_stop_losses actualizează current_price pentru pozițiile păstrate;
- cu USE_STOP_LOSS=False, acea funcție este ocolită;
- process_daily_prices există dar nu este apelată în run_simulation prezentată;
- current_price rămâne la intrare pentru pozițiile deschise;
- equity, drawdown, expuneri, sizing ulterior și PNL nerealizat nu reflectă corect piața.

B. Buget agregat de risc neaplicat:
- new_position_risk este corect normalizat la equity;
- current_risk_used este însă întotdeauna 0.0;
- suma riscurilor pozițiilor existente nu este verificată față de 2%.
- cu stop dezactivat, riscul ATR este doar o referință de sizing, nu limită de pierdere executată.

C. Filtru volum suplimentar fix:
- run_simulation respinge volume_ratio<2.5;
- Optuna explorează 1.5,2,2.5 în generator, dar nu schimbă constanta simulatorului;
- pragurile mai mici nu permit execuții sub 2.5 în acest flux. Best min_volume_ratio=1.5 nu dovedește tranzacționare la acel prag.

D. Calendar train/test:
- iterează toate datele din istoricul transmis;
- tranzacții train pot ieși după 2025-01-01;
- perioada equity nu este izolată automat pe split;
- nu declara validare out-of-sample strictă înainte de remediere/verificare.

E. Modele auxiliare nealiniate:
- simulate_position folosește altă formulă de net_return decât close_position;
- verifică low inclusiv pe ziua ieșirii planificate, deși ieșirea normală este la open;
- execuția stopului la preț exact, fără tratament vizibil pentru gap sub stop;
- funcții de test și self-import sunt inserate în modulul operațional. Nu presupune că testele sunt executate automat la rulare.

F. Reconciliere:
- afișează cash inițial - costuri intrări + încasări ieșiri versus cash final;
- nu conține assert în fragment;
- nu validează mark-to-market, strategia sau toate metricile.

Niciuna dintre aceste probleme nu a fost corectată în etapa de documentare din 16 octombrie. Nu relansa Optuna înainte de salvarea stării și definirea testelor/corecțiilor.

## 10. Home Assistant și MQTT

### 10.1 Entități păstrate / retrase

Păstrate conform conversației:
- sensor.bvb_atr_portfolio_mqtt;
- sensor.bvb_info_ultima_actualizare.

Retrase anterior:
- sensor.bvb_strategy_bvb_strategy_status: șters prin payload gol retained pe homeassistant/sensor/bvb_strategy/status/config; dispariție confirmată.
- automatizarea BVB – Buget de risc epuizat: ștergere confirmată de utilizator.
- sensor.bvb_atr_portfolio și definiția YAML sensor.bvb_risk_status: retragerea a fost raportată în rezumatul conversației, fără aceeași verificare directă în secvența curentă.

### 10.2 Componente provizorii existente

- /home/bvb/bvb-info/build_portfolio_notifications.py, creat și rulat cu succes;
- publică portfolio/performance și, dacă există, portfolio/actions prin clientul MQTT existent;
- automatizare BVB – Raport zilnic portofoliu: funcțională, notificare iPhone confirmată;
- BVB – Semnal portofoliu: YAML furnizat, existență verificată separat neconfirmată;
- senzor BVB Portfolio Performance, unique_id bvb_portfolio_performance, ID așteptat sensor.bvb_portfolio_performance; apariția cardului confirmată;
- dashboard vertical-stack: BVB · Starea datelor și BVB · Performanță simulată;
- afișarea notificării a fost corectată cu YAML message: |- în loc de caractere literale \n.

Nu s-a confirmat ștergerea/dezactivarea acestora. Utilizatorul a oprit planul de curățare; se păstrează.

Payloadul actual de performanță provine din istoricul simulat, nu din portofoliul real/virtual nou.
Raportul folosește ultima observație din atr_dynamic_equity_curve sau daily_equity_curve; generated_at nu garantează actualitatea pieței.
Comparațiile sunt ferestre de 7/30 zile calendaristice ancorate la ultima observație, nu săptămână/lună calendaristică.
Scriptul nu implementează complet validarea actualității și a acțiunilor, nici deduplicarea semnalelor. Nu îl trata ca motor de ordine.

### 10.3 Topicuri distincte

- homelab/bvb-info/update/status: ultima actualizare bvb-info;
- homelab/bvb-info/strategy/status: vechiul status de strategie;
- homelab/bvb-info/portfolio/performance: raport provizoriu;
- homelab/bvb-info/portfolio/actions: propuneri provizorii dacă există;
- bvb/atr_portfolio/status: publicare worker confirmată în logul din 15 octombrie.

publicare MQTT reușită != date de piață actuale sau strategie validată.

## 11. Portofoliul virtual — cerințe, NU implementare confirmată

Utilizatorul dorește:
- portofoliu separat cu capital 100000; moneda RON propusă în context;
- BUY/SELL cu simbol, preț de referință, cantitate și motiv;
- cantitate editabilă, separată de propunerea strategiei;
- selectarea tuturor sau unei părți din propuneri;
- buton Finalizează sesiunea: un lot, nu notificare/execuție după fiecare selecție;
- validare backend a cashului, expunerilor, riscului și cantităților deținute;
- rezultat consolidat și performanță zi/săptămână/lună;
- modul exclusiv de test, resetabil/arhivabil/dezinstalabil;
- fără broker real.

Discussed, not implemented:
- registru de portofoliu, sesiuni, executor virtual, butoane de aprobare/respingere, input-uri de cantitate;
- ID-uri unice, session_revision/schema_version, deduplicare, row locking, rezervări;
- reguli de execuție la următoarea deschidere și toleranțe de preț;
- schema bvb_paper pentru registrul virtual.

Nu trata discuțiile de arhitectură ca fișiere/procese deja instalate. Nu s-au trimis ordine reale în pașii confirmați.

## 12. Backupuri confirmate

### bvb-info
- backups/price_fix_20261015_184722/ : numbers.py și pipeline.py dinainte de primul patch;
- backups/before_regs_save_20261015_190111_158576/daily_prices.json : cele 170 de rânduri existente înainte de salvarea filtrată;
- backups/regs_filter_<timestamp>/ : backup pipeline înainte de filtrarea persistentă; timestamp exact necomunicat.

### Worker și DB
- /home/bvb/bvb-backups/20261015_191714/bvb_data.dump
  Dimensiune raportată 867969 bytes.
- /home/bvb/bvb-backups/code_20261015_192330_pWM0aY/
  Backup creat și verificat; arhive cod, raw/clean, tracked_changes.patch, git_status.txt, SHA256SUMS conform comenzii executate.
- Snapshotul de cod nu include .env și nu este o clonă completă cu istoricul .git.
- Backupul bvb_data nu acoperă baza bvb_info sau Home Assistant.
- Existența unui backup HA nou nu a fost confirmată.

## 13. Git / fișiere existente, fără concluzii de ștergere

Ultimul status worker arăta M:
- scripts/daily.sh
- src/atr_portfolio_simulator.py
- tests/test_atr_position_exit.py
- tests/test_atr_position_sizing.py

Ne urmărite de Git, între altele:
- config/, data/;
- scripts/backfill_bvb_history.py, fetch_bvb_history_yahoo.py;
- optimize_strategy.py, generate_atr_portfolio_signals.py, run_atr_portfolio_simulation.py;
- build_atr_performance_report.py, build_walk_forward_report.py;
- run_matched_stop_sensitivity.py, run_stop_atr_sensitivity.py, run_volume_ratio_sensitivity.py;
- scan_baseline_horizons.py, summarize_atr_portfolio.py, publish_strategy.py;
- teste noi și fișiere .bak.

Prezența lor nu demonstrează cine le-a creat sau că sunt redundante. Nu au fost șterse în pașii confirmați.

## 14. Repere istorice din documentul anterior

Se păstrează numai ca rezultate istorice, nu ca validare a configurației curente Optuna:
- 43 tranzacții în baseline-ul istoric 2021–2026;
- baseline dinamic stop 8%: win rate 60.47%, PF 2.3676, drawdown trade-by-trade -15.36%, final equity normalizat 2.3129526268565406, 5 stopuri;
- snapshotul metrics din 14 octombrie: daily și ATR daily drawdown ambele -0.14609721204508186, 150 puncte fiecare;
- risk_status.date=2026-09-09, status=HISTORICAL_SIMULATION_ONLY;
- aceste metrici din metrics_generator sunt o cale diferită de runnerul ATR CSV analizat. Nu atribui automat bugurile sau rezultatele uneia celeilalte fără inspecție.
- fișierele portfolio_metrics_stop8.json / baseline.json cu 5 tranzacții provin din trades_sample.csv, nu din portofoliul actual.
- documentația veche descria ajustări corporate actions, dar aplicarea efectivă era încă neimplementată. Starea actuală nu a fost reverificată.

## 15. Următorii pași recomandați, fără execuție implicită

1. Încărcarea acestui document în proiect în locul snapshotului vechi; păstrarea unei copii locale a celui vechi pentru audit.
2. Nicio ștergere/dezactivare generală a automatizărilor sau datelor.
3. Salvarea artefactelor Optuna și a stării codului înaintea oricărei corecții.
4. Verificare pe disc pentru import sys lipsă și verificarea funcțiilor neinspectate complet, inclusiv calculate_atr/get_all_trading_dates/get_trades_for_date.
5. Plan de teste pentru mark-to-market, agregarea riscului, prag volum, split temporal și reconciliere PNL/cash.
6. Stabilirea regulilor înaintea modificării; corectarea lor în componente existente, nu noi scripturi paralele fără necesitate.
7. Revalidarea sursei istorice: răspuns gol nu înseamnă piață fără date; nu pretinde backfill complet.
8. Abia apoi rerulare comparativă train/test și integrare operațională, cu versiuni de cod/date și rezultate păstrate separat.

## 16. Ce NU se poate afirma în acest moment

- Că strategia este profitabilă out-of-sample sau pregătită pentru producție.
- Că parametrii salvați Optuna sunt cei folosiți zilnic.
- Că pragul 1.5 a fost realmente evaluat ca prag efectiv de execuție.
- Că drawdown-ul Optuna este mark-to-market corect.
- Că riscul agregat de 2% este impus.
- Că backfill-ul a recuperat toate zilele lipsă.
- Că portofoliul virtual și aprobarea HA sunt implementate.
- Că schema/view-ul provizoriu bvb_paper există.
- Că automatizările au fost șterse după oprirea planului de curățare.

Sfârșitul documentului. Acesta documentează starea observată; nu aplică modificări.
