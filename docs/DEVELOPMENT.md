# Dezvoltare si instalare

## Cerinte

- Linux sau Debian.
- Python 3.
- PostgreSQL.
- Git.

## Activarea mediului virtual

cd /home/bvb/bvb-data-worker
source .venv/bin/activate

## Verificarea mediului

python --version
pip --version

## Structura proiectului

- src/: codul aplicatiei.
- db/migrations/: schema bazei de date.
- data/raw/: fisiere CSV originale.
- data/clean/: fisiere CSV validate si filtrate.
- docs/: documentatia proiectului.

## Comenzi utile

Pornire colectare date:

python src/fetch_bvb.py

Verificarea testelor:

pytest

Verificarea modificarilor Git:

git status --short

## Reguli de dezvoltare

- Nu modifica datele raw dupa import.
- Pastreaza modificarile de schema in migrations/.
- Valideaza datele inainte de inserarea in prices_daily.
- Documenteaza deciziile importante in docs/adr/.

## Testare

Testele unitare și de integrare pot fi rulate cu:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Pentru rularea exclusivă a testului PostgreSQL:

```bash
PYTHONPATH=src .venv/bin/pytest -q -m integration
```

Testul de integrare necesită `DATABASE_URL` configurat și trebuie rulat numai împotriva unei baze de test sau development, nu împotriva producției.

Pentru a verifica testele marcate și rezultatele detaliate:

```bash
PYTHONPATH=src .venv/bin/pytest -q -m integration -rs
```

## Structura operationala actuala

- src/fetch_bvb.py: colectarea zilnica BVB.
- src/metrics_generator.py: generarea metricilor istorice dinamice.
- scripts/daily.sh: pipeline zilnic; ruleaza fetch si metrics generator.
- generate_trades_from_history.py: utilitar pentru generarea tranzactiilor istorice.
- src/import_legacy_tradeville.py: importul istoricului TradeVille.
- src/probe_retention.py: utilitar de verificare a retentiei datelor.
- db/migrations/005_historical_ohlcv.sql: tabela istoric OHLCV.
- output/: artefacte regenerate, ignorate in Git.
- output/portfolio_metrics_history_stop8_dynamic_baseline.json: baseline dinamic local.

## Fluxul zilnic

1. scripts/daily.sh ruleaza src/fetch_bvb.py.
2. scripts/daily.sh ruleaza src/metrics_generator.py.
3. Rezultatele sunt scrise in output/portfolio_metrics_history_stop8.json.
4. Cron ruleaza pipeline-ul in zilele lucratoare la 18:35.
