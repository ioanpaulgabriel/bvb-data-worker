# Operare

## Scop

Acest document descrie rularea zilnica, verificarile si recuperarea proiectului.

## Rulare manuala

cd /home/bvb/bvb-data-worker
source .venv/bin/activate
python src/fetch_bvb.py

## Verificari dupa rulare

- Confirma ca exista un CSV nou in data/raw/.
- Confirma ca exista un CSV nou in data/clean/.
- Verifica numarul de randuri importate.
- Verifica eventualele erori din loguri.
- Confirma ca datele pentru REGS au fost procesate.

## Verificarea bazei de date

Verifica ultima data disponibila in prices_daily si numarul de randuri pentru acea data.

Compara numarul de randuri din CSV-ul curatat cu numarul de randuri inserate in prices_daily.

## Backup

Backup-ul bazei de date trebuie facut inainte de modificari de schema sau operatii de reparare.

Exemplu:

pg_dump DATABASE_NAME > backup.sql

## Recuperare

Pentru restaurare se foloseste un backup verificat:

psql DATABASE_NAME < backup.sql

Dupa restaurare, verifica schema, numarul de randuri si ultima data importata.

## Regula de siguranta

Nu sterge fisierele din data/raw/ si nu modifica manual preturile originale din prices_daily.
